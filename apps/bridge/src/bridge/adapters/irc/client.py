"""IRC client: pydle-based with IRCv3 support."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import os
import random
from collections.abc import Callable
from typing import ClassVar

import pydle
from cachetools import TTLCache
from loguru import logger

from bridge.adapters.irc.msgid import MessageIDTracker, ReactionTracker
from bridge.adapters.irc.throttle import TokenBucket
from bridge.config import cfg
from bridge.events import MessageOut
from bridge.gateway import Bus, ChannelRouter

# IRC color codes (Mirc color palette indices 2-13; skip 0=white, 1=black for readability)
_IRC_NICK_COLORS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]


def _nick_color(nick: str) -> str:
    """Wrap nick in a deterministic IRC color based on a hash of the nick."""
    idx = int(hashlib.md5(nick.encode(), usedforsecurity=False).hexdigest(), 16) % len(_IRC_NICK_COLORS)
    code = _IRC_NICK_COLORS[idx]
    return f"\x03{code:02d}{nick}\x03"


# Backoff: min 2s, max 60s, jitter (exported for tests)
_BACKOFF_MIN = 2
_BACKOFF_MAX = 60
_MAX_ATTEMPTS = 10


async def _connect_with_backoff(
    client: pydle.Client,
    hostname: str,
    port: int,
    tls: bool,
    tls_verify: bool = True,
) -> None:
    """Connect with exponential backoff and jitter on failure; reconnect on disconnect."""
    attempt = 0
    while True:
        try:
            await client.connect(
                hostname=hostname,
                port=port,
                tls=tls,
                tls_verify=tls_verify,
            )
            # pydle.connect() returns immediately after spawning handle_forever.
            # Wait for actual disconnect before reconnecting.
            while client.connected:
                await asyncio.sleep(0.5)
            attempt = 0
            delay = min(_BACKOFF_MAX, _BACKOFF_MIN)
            jitter = random.uniform(0.5, 1.5)
            wait = delay * jitter
            logger.info("IRC disconnected, reconnecting in {:.1f}s", wait)
            await asyncio.sleep(wait)
        except Exception as exc:
            attempt += 1
            if attempt >= _MAX_ATTEMPTS:
                logger.exception("IRC connect failed after {} attempts", _MAX_ATTEMPTS)
                raise
            delay = min(_BACKOFF_MAX, _BACKOFF_MIN * (2 ** (attempt - 1)))
            jitter = random.uniform(0.5, 1.5)
            wait = delay * jitter
            logger.warning(
                "IRC connect failed (attempt {}): {}, retrying in {:.1f}s",
                attempt,
                exc,
                wait,
            )
            await asyncio.sleep(wait)


class IRCClient(pydle.Client):
    """Pydle IRC client with IRCv3 capabilities."""

    CAPABILITIES: ClassVar[set[str]] = {
        "message-tags",  # IRCv3: structured key-value tags on messages (required for msgid)
        "msgid",  # IRCv3: server-assigned unique message IDs (for REDACT/edit correlation)
        "account-notify",  # IRCv3: notifications when users authenticate to services
        "extended-join",  # IRCv3: includes account name in JOIN messages
        "server-time",  # IRCv3: server-side timestamps (for history replay detection)
        "draft/reply",  # IRCv3: reply threading via +draft/reply tag
        "draft/message-redaction",  # IRCv3: REDACT command for message deletion
        "draft/react",  # IRCv3: emoji reactions via TAGMSG +draft/react
        "batch",  # IRCv3: batch message grouping
        "echo-message",  # IRCv3: server echoes our own messages back (for msgid capture)
        "labeled-response",  # IRCv3: correlate server responses to our commands via labels
        "chghost",  # IRCv3: host change notifications (no reconnect needed)
        "setname",  # IRCv3: realname change notifications
        "draft/relaymsg",  # IRCv3: stateless bridging — send as spoofed nick without puppets
        "overdrivenetworks.com/relaymsg",  # Alternate relaymsg cap name (some networks)
        "cap-notify",  # IRCv3: notify when caps are added/removed at runtime
        "bot",  # IRCv3: bot mode — mark ourselves as a bot, see bot tags on others
        "draft/multiline",  # IRCv3: send multi-line messages as a single batch
        "draft/chathistory",  # IRCv3: fetch missed messages on reconnect via CHATHISTORY
    }

    def __init__(
        self,
        bus: Bus,
        router: ChannelRouter,
        server: str,
        nick: str,
        channels: list[str],
        msgid_tracker: MessageIDTracker,
        reaction_tracker: ReactionTracker,
        throttle_limit: int = 10,
        rejoin_delay: float = 5,
        auto_rejoin: bool = True,
        **kwargs,
    ):
        super().__init__(nick, **kwargs)
        self._bus = bus
        self._router = router
        self._server = server
        self._channels = channels
        self._initial_nick = nick  # for nick revert after forced rename
        self._outbound: asyncio.Queue[MessageOut] = asyncio.Queue()
        self._consumer_task: asyncio.Task | None = None
        self._msgid_tracker = msgid_tracker
        self._reaction_tracker = reaction_tracker
        self._throttle = TokenBucket(limit=throttle_limit, refill_rate=float(throttle_limit))
        self._rejoin_delay = rejoin_delay
        self._auto_rejoin = auto_rejoin
        self._ready = False
        self._pending_sends: asyncio.Queue[str] = asyncio.Queue()  # discord_id for echo correlation
        self._message_tags: dict[str, str | bool | None] = {}  # set in on_raw_privmsg from message.tags
        self._puppet_nick_check: Callable[[str], bool] | None = None  # set by adapter for echo detection
        # Fallback echo detection when relaymsg tag missing (e.g. via irc-services)
        self._recent_relaymsg_sends: TTLCache[tuple[str, str], None] = TTLCache(maxsize=100, ttl=5)
        # labeled-response: label counter and pending label→discord_id mapping for echo correlation.
        # When we send a RELAYMSG/PRIVMSG with a label tag, the server echoes it back with the
        # same label. We match the echo's label to the discord_id we stored, enabling reliable
        # msgid→discord_id correlation even when multiple messages are in flight.
        self._label_counter: int = 0
        self._pending_labels: TTLCache[str, str] = TTLCache(maxsize=200, ttl=30)  # label -> discord_id
        # ISUPPORT values (Requirement 11.7, 11.8)
        self._server_nicklen: int = 23  # effective limit: min(server_nicklen, 23)
        self._server_casemapping: str = "rfc1459"  # default per IRC spec
        # Nick collision retry counter (used by handlers.handle_nick_collision)
        self._nick_collision_attempts: int = 0
        # Multiline batch counter for draft/multiline BATCH references
        self._batch_counter: int = 0
        # Chathistory: track last message timestamp per channel for CHATHISTORY AFTER on reconnect
        self._last_message_times: dict[str, str] = {}
        # Active chathistory batch references — messages in these batches bypass history replay suppression
        self._chathistory_batches: set[str] = set()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def on_connect(self):
        """After connect, join channels and start consumer."""
        await super().on_connect()
        self._ready = False
        logger.info("IRC connected to {}", self._server)
        for channel in self._channels:
            try:
                await self.join(channel)
            except Exception as exc:
                logger.warning("IRC: failed to join {}: {} (will retry on next reconnect)", channel, exc)
        await self._ensure_channels_permanent()
        self._consumer_task = asyncio.create_task(self._consume_outbound())
        # Fallback: if no PONG within 10s, mark ready anyway (some servers don't echo PING)
        asyncio.create_task(self._ready_fallback())  # noqa: RUF006
        # Fetch missed messages via CHATHISTORY on reconnect (if we have prior timestamps)
        if self._last_message_times:
            asyncio.create_task(self._fetch_chathistory())  # noqa: RUF006

    async def _ensure_channels_permanent(self) -> None:
        """OPER up, set +B (bot mode), and set +P (permanent) on bridged channels."""
        oper_password = os.environ.get("BRIDGE_IRC_OPER_PASSWORD", "").strip()
        if not oper_password:
            return
        oper_name = "bridge"  # Must match oper block in UnrealIRCd
        try:
            await self.rawmsg("OPER", oper_name, oper_password)
            await asyncio.sleep(1)  # Allow server to process OPER
            # Set bot mode on ourselves so we appear as a bot to IRC users
            await self.rawmsg("MODE", self.nickname, "+B")
            logger.info("IRC: set +B (bot mode) on {}", self.nickname)
            for channel in self._channels:
                await self.rawmsg("MODE", channel, "+P")
                await self.rawmsg("MODE", channel, "+H", "50:1d")  # Required for REDACT (chathistory)
                logger.info("Set {} permanent (+P) and history (+H 50:1d)", channel)
        except Exception as exc:
            logger.warning("Could not set channels permanent (OPER/MODE): {}", exc)

    async def _ready_fallback(self) -> None:
        await asyncio.sleep(10)
        if not self._ready:
            self._ready = True
            logger.debug("IRC ready (fallback timeout)")

    async def on_raw_005(self, message):
        """After 005 ISUPPORT, parse NICKLEN/CASEMAPPING and send PING for ready detection."""
        await super().on_raw_005(message)
        # Parse ISUPPORT tokens (Requirement 11.7, 11.8)
        params = getattr(message, "params", [])
        for token in params:
            token_str = str(token)
            if token_str.startswith("NICKLEN="):
                try:
                    server_nicklen = int(token_str.split("=", 1)[1])
                    self._server_nicklen = min(server_nicklen, 23)
                    logger.debug("IRC ISUPPORT: NICKLEN={} (effective={})", server_nicklen, self._server_nicklen)
                except (ValueError, IndexError):
                    pass
            elif token_str.startswith("CASEMAPPING="):
                mapping_val = token_str.split("=", 1)[1].lower()
                if mapping_val in ("ascii", "rfc1459", "rfc1459-strict"):
                    self._server_casemapping = mapping_val
                    logger.debug("IRC ISUPPORT: CASEMAPPING={}", self._server_casemapping)
        await self.rawmsg("PING", "ready")

    # ------------------------------------------------------------------
    # No-op numeric handlers (suppress "Unknown command" warnings)
    # ------------------------------------------------------------------

    async def on_raw_396(self, message: object) -> None:
        """RPL_HOSTHIDDEN: host change notice (InspIRCd/UnrealIRCd). No-op to avoid Unknown command."""
        pass

    async def on_raw_379(self, message: object) -> None:
        """RPL_WHOISHOST: mode info in WHOIS. No-op to avoid Unknown command."""
        pass

    async def on_raw_320(self, message: object) -> None:
        """RPL_WHOIS (320): UnrealIRCd sends security-groups/WEBIRC info. No-op to avoid Unknown command."""
        pass

    async def on_raw_381(self, message: object) -> None:
        """RPL_YOUREOPER (381): You are now an IRC Operator. No-op to avoid Unknown command."""
        pass

    # ------------------------------------------------------------------
    # Ready detection
    # ------------------------------------------------------------------

    async def on_raw_pong(self, message) -> None:
        """Mark ready when we receive PONG ready (echo of our PING)."""
        await super().on_raw_pong(message)
        params = getattr(message, "params", [])
        if params and "ready" in (str(p) for p in params):
            self._ready = True
            logger.debug("IRC ready (PONG received)")

    # ------------------------------------------------------------------
    # PRIVMSG tag extraction (coupling: sets _message_tags for on_message)
    # ------------------------------------------------------------------

    async def on_raw_privmsg(self, message) -> None:
        """Set _message_tags from parsed message so on_message can read msgid/draft/relaymsg."""
        self._message_tags = getattr(message, "tags", None) or {}
        if self._message_tags:
            params = getattr(message, "params", [])
            target = params[0] if params else "?"
            logger.debug(
                "IRC: PRIVMSG to {} with tags={}",
                target,
                self._message_tags,
            )
        try:
            await super().on_raw_privmsg(message)
        finally:
            self._message_tags = {}

    # ------------------------------------------------------------------
    # Disconnect / cleanup
    # ------------------------------------------------------------------

    async def on_disconnect(self, expected: bool) -> None:
        """Handle disconnect; rejoin channels on reconnect."""
        await super().on_disconnect(expected)
        self._ready = False

    async def disconnect(self, expected=True):
        """Disconnect and cleanup."""
        if self._consumer_task:
            self._consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._consumer_task
        await super().disconnect(expected)

    # ------------------------------------------------------------------
    # Capability negotiation
    # ------------------------------------------------------------------

    async def on_capability_message_tags_available(self, value):
        """Request message-tags (required for msgid on PRIVMSG/RELAYMSG)."""
        logger.info("IRC: requesting message-tags capability (value={})", value)
        return True

    async def on_capability_message_tags_5_0_available(self, value):
        """Request message-tags when UnrealIRCd advertises as message-tags:5.0."""
        logger.info("IRC: requesting message-tags:5.0 capability (value={})", value)
        return True

    async def on_raw_cap_ls(self, params):
        """Skip '*' sentinel (multi-line CAP LS) so pydle doesn't send CAP END prematurely.
        Always request message-tags (req for msgid) since UnrealIRCd may send it in a batch we process after our REQ."""
        if not params or not params[0]:
            await super().on_raw_cap_ls(params)
            return
        batch = params[0].strip()
        if batch == "*":
            logger.debug("IRC: skipping CAP LS sentinel '*' (multi-line; waiting for real batches)")
            return
        await super().on_raw_cap_ls(params)
        # Ensure we request message-tags; UnrealIRCd may send it in a later batch but we need it for msgid.
        caps = getattr(self, "_capabilities", {})
        if caps.get("message-tags") is None and "message-tags" not in getattr(self, "_capabilities_requested", set()):
            logger.debug("IRC: explicitly requesting message-tags (required for msgid)")
            self._capabilities_requested.add("message-tags")
            await self.rawmsg("CAP", "REQ", "message-tags")

    async def on_capability_message_tags_enabled(self):
        """Log when message-tags capability is negotiated (required for msgid on PRIVMSG)."""
        logger.info("IRC: message-tags capability negotiated")

    async def on_capability_draft_message_redaction_available(self, value):
        """Request draft/message-redaction for REDACT (message deletion)."""
        return True

    async def on_capability_draft_relaymsg_enabled(self):
        """Log when draft/relaymsg is negotiated."""
        logger.debug("IRC: draft/relaymsg capability negotiated")

    async def on_capability_labeled_response_available(self, value):
        """Request labeled-response for echo correlation (Requirement 11.5)."""
        return True

    async def on_capability_labeled_response_enabled(self):
        """Log when labeled-response is negotiated."""
        logger.debug("IRC: labeled-response capability negotiated")

    def _has_labeled_response(self) -> bool:
        """Check if labeled-response capability was negotiated."""
        caps = getattr(self, "_capabilities", {})
        return bool(caps.get("labeled-response"))

    def _next_label(self) -> str:
        """Generate the next unique label for labeled-response."""
        self._label_counter += 1
        return f"bridge-{self._label_counter}"

    # ------------------------------------------------------------------
    # cap-notify, bot, multiline, chathistory capability handlers
    # ------------------------------------------------------------------

    async def on_capability_cap_notify_available(self, value):
        """Request cap-notify for runtime capability change notifications."""
        return True

    async def on_capability_bot_available(self, value):
        """Request bot capability — marks us as a bot, lets us see bot tags on others."""
        return True

    async def on_capability_bot_enabled(self):
        """Log when bot capability is negotiated."""
        logger.debug("IRC: bot capability negotiated")

    async def on_capability_draft_multiline_available(self, value):
        """Request draft/multiline for sending multi-line messages as a single batch."""
        return True

    async def on_capability_draft_multiline_enabled(self):
        """Log when draft/multiline is negotiated."""
        logger.info("IRC: draft/multiline capability negotiated — multi-line batches enabled")

    def _has_multiline(self) -> bool:
        """Check if draft/multiline capability was negotiated."""
        caps = getattr(self, "_capabilities", {})
        return bool(caps.get("draft/multiline"))

    def _next_batch_ref(self) -> str:
        """Generate the next unique batch reference tag for BATCH commands."""
        self._batch_counter += 1
        return f"bridge-ml-{self._batch_counter}"

    async def on_capability_draft_chathistory_available(self, value):
        """Request draft/chathistory for fetching missed messages on reconnect."""
        return True

    async def on_capability_draft_chathistory_enabled(self):
        """Log when draft/chathistory is negotiated."""
        logger.info("IRC: draft/chathistory capability negotiated — reconnect history enabled")

    def _has_chathistory(self) -> bool:
        """Check if draft/chathistory capability was negotiated."""
        caps = getattr(self, "_capabilities", {})
        return bool(caps.get("draft/chathistory"))

    async def _fetch_chathistory(self) -> None:
        """Fetch missed messages via CHATHISTORY AFTER on reconnect.

        Waits for the client to be ready, then issues CHATHISTORY AFTER for
        each channel that has a stored last-message timestamp. Messages arrive
        in a chathistory batch and bypass history replay suppression.
        """
        if not cfg.irc_chathistory_on_reconnect:
            return
        # Wait for ready (caps negotiated, channels joined)
        for _ in range(30):
            if self._ready:
                break
            await asyncio.sleep(0.5)
        if not self._has_chathistory():
            logger.debug("IRC: draft/chathistory not negotiated; skipping reconnect history fetch")
            return
        limit = str(cfg.irc_chathistory_limit)
        for channel in self._channels:
            last = self._last_message_times.get(channel)
            if not last:
                continue
            try:
                await self.rawmsg("CHATHISTORY", "AFTER", channel, f"timestamp={last}", limit)
                logger.info("IRC: requested CHATHISTORY AFTER {} since {}", channel, last)
            except Exception as exc:
                logger.warning("IRC: CHATHISTORY request failed for {}: {}", channel, exc)

    # ------------------------------------------------------------------
    # BATCH handler (chathistory batch tracking)
    # ------------------------------------------------------------------

    async def on_raw_batch(self, message) -> None:
        """Track chathistory batch start/end for history replay suppression bypass."""
        params = getattr(message, "params", [])
        if not params:
            return
        ref_tag = str(params[0])
        if ref_tag.startswith("+"):
            # Batch start: +ref type [params...]
            ref = ref_tag[1:]
            batch_type = params[1] if len(params) > 1 else ""
            if batch_type == "chathistory":
                self._chathistory_batches.add(ref)
                logger.debug("IRC: chathistory batch started ref={}", ref)
        elif ref_tag.startswith("-"):
            # Batch end: -ref
            ref = ref_tag[1:]
            if ref in self._chathistory_batches:
                self._chathistory_batches.discard(ref)
                logger.debug("IRC: chathistory batch ended ref={}", ref)

    async def on_capability_draft_relaymsg_available(self, value):
        """Request draft/relaymsg for stateless bridging."""
        return True

    async def on_capability_overdrivenetworks_com_relaymsg_available(self, value):
        """Request overdrivenetworks.com/relaymsg (alternate relaymsg cap name)."""
        return True

    # ------------------------------------------------------------------
    # RELAYMSG helpers
    # ------------------------------------------------------------------

    def _has_relaymsg(self) -> bool:
        """Check if RELAYMSG capability was negotiated."""
        caps = getattr(self, "_capabilities", {})
        return bool(caps.get("draft/relaymsg") or caps.get("overdrivenetworks.com/relaymsg"))

    def _sanitize_relaymsg_nick(self, nick: str) -> str:
        """Sanitize nick for RELAYMSG: replace invalid chars with '-'.

        When irc_relaymsg_clean_nicks is enabled (server allows clean nicks
        without a separator), the nick is used as-is. Otherwise, '/d' is
        appended because Valware's relaymsg implementation requires a '/'
        separator in the spoofed nick to distinguish it from real users.
        """
        invalid = " \t\n\r!+%@&#$:'\"?*,."
        out = "".join("-" if c in invalid else c for c in nick)
        out = (out or "user")[:32]
        if "/" not in out and not cfg.irc_relaymsg_clean_nicks:
            out = f"{out}/d"
        return out

    # ------------------------------------------------------------------
    # Outbound queue
    # ------------------------------------------------------------------

    def queue_message(self, evt: MessageOut):
        """Queue outbound message."""
        logger.info("IRC: queued message for channel={}", evt.channel_id)
        self._outbound.put_nowait(evt)

    # ------------------------------------------------------------------
    # Thin delegation stubs — inbound handlers (→ handlers.py)
    # ------------------------------------------------------------------

    async def on_message(self, target, source, message):
        """Handle channel message — delegates to handlers.handle_message."""
        await super().on_message(target, source, message)
        from bridge.adapters.irc.handlers import handle_message

        await handle_message(self, target, source, message)

    async def on_ctcp_action(self, by, target, message):
        """Handle /me action — delegates to handlers.handle_ctcp_action."""
        await super().on_ctcp_action(by, target, message)
        from bridge.adapters.irc.handlers import handle_ctcp_action

        await handle_ctcp_action(self, by, target, message)

    async def on_ctcp_version(self, by, target, contents):
        """Respond to CTCP VERSION — delegates to handlers.handle_ctcp_version."""
        from bridge.adapters.irc.handlers import handle_ctcp_version

        await handle_ctcp_version(self, by, target, contents)

    async def on_ctcp_source(self, by, target, contents):
        """Respond to CTCP SOURCE — delegates to handlers.handle_ctcp_source."""
        from bridge.adapters.irc.handlers import handle_ctcp_source

        await handle_ctcp_source(self, by, target, contents)

    async def on_raw_tagmsg(self, message) -> None:
        """Handle TAGMSG — delegates to handlers.handle_tagmsg."""
        from bridge.adapters.irc.handlers import handle_tagmsg

        await handle_tagmsg(self, message)

    async def on_raw_redact(self, message) -> None:
        """Handle REDACT — delegates to handlers.handle_redact."""
        from bridge.adapters.irc.handlers import handle_redact

        await handle_redact(self, message)

    async def on_kick(self, channel: str, target: str, by: str, reason: str | None = None) -> None:
        """Handle KICK — delegates to handlers.handle_kick."""
        await super().on_kick(channel, target, by, reason or "")
        from bridge.adapters.irc.handlers import handle_kick

        await handle_kick(self, channel, target, by, reason)

    async def on_nick(self, old: str, new: str) -> None:
        """Handle nick change — delegates to handlers.handle_nick."""
        await super().on_nick(old, new)
        from bridge.adapters.irc.handlers import handle_nick

        await handle_nick(self, old, new)

    async def on_raw_chghost(self, message):
        """Handle CHGHOST — delegates to handlers.handle_chghost."""
        from bridge.adapters.irc.handlers import handle_chghost

        await handle_chghost(self, message)

    async def on_raw_setname(self, message):
        """Handle SETNAME — delegates to handlers.handle_setname."""
        from bridge.adapters.irc.handlers import handle_setname

        await handle_setname(self, message)

    # ------------------------------------------------------------------
    # Nick collision handling (Requirement 20.1, 20.2, 20.3)
    # ------------------------------------------------------------------

    async def on_raw_433(self, message) -> None:
        """ERR_NICKNAMEINUSE (433): try alternative nicks with suffix escalation."""
        from bridge.adapters.irc.handlers import handle_nick_collision

        await handle_nick_collision(self, message, error_code=433)

    async def on_raw_432(self, message) -> None:
        """ERR_ERRONEUSNICKNAME (432): re-sanitize and retry."""
        from bridge.adapters.irc.handlers import handle_nick_collision

        await handle_nick_collision(self, message, error_code=432)

    # ------------------------------------------------------------------
    # Thin delegation stubs — outbound (→ outbound.py)
    # ------------------------------------------------------------------

    async def _consume_outbound(self):
        """Consume outbound queue — delegates to outbound.consume_outbound."""
        from bridge.adapters.irc.outbound import consume_outbound

        await consume_outbound(self)

    async def _send_message(self, evt: MessageOut):
        """Send message to IRC — delegates to outbound.send_message."""
        from bridge.adapters.irc.outbound import send_message

        await send_message(self, evt)
