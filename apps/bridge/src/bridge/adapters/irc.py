"""IRC adapter: pydle-based with IRCv3 support."""

from __future__ import annotations

import asyncio
import contextlib
import os
import random
from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar

import pydle
from cachetools import TTLCache
from loguru import logger

from bridge.adapters.irc_msgid import MessageIDTracker, ReactionTracker
from bridge.adapters.irc_puppet import IRCPuppetManager
from bridge.adapters.irc_throttle import TokenBucket
from bridge.config import cfg
from bridge.events import MessageDeleteOut, MessageOut, ReactionOut, TypingOut, message_in
from bridge.formatting.irc_message_split import split_irc_message
from bridge.gateway import Bus, ChannelRouter

if TYPE_CHECKING:
    from bridge.identity import IdentityResolver

# Backoff: min 2s, max 60s, jitter
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
        "message-tags",
        "msgid",
        "account-notify",
        "extended-join",
        "server-time",
        "draft/reply",
        "draft/message-redaction",
        "draft/react",
        "batch",
        "echo-message",
        "labeled-response",
        "chghost",
        "setname",
        "draft/relaymsg",
        "overdrivenetworks.com/relaymsg",
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
        self._outbound: asyncio.Queue[MessageOut] = asyncio.Queue()
        self._consumer_task: asyncio.Task | None = None
        self._msgid_tracker = msgid_tracker
        self._reaction_tracker = reaction_tracker
        self._throttle = TokenBucket(limit=throttle_limit, refill_rate=float(throttle_limit))
        self._rejoin_delay = rejoin_delay
        self._auto_rejoin = auto_rejoin
        self._ready = False
        self._pending_sends: asyncio.Queue[str] = asyncio.Queue()  # discord_id for echo correlation
        self._message_tags: dict[str, str | bool] = {}  # set in on_raw_privmsg from message.tags
        self._puppet_nick_check: Callable[[str], bool] | None = None  # set by adapter for echo detection
        # Fallback echo detection when relaymsg tag missing (e.g. via irc-services)
        self._recent_relaymsg_sends: TTLCache[tuple[str, str], None] = TTLCache(maxsize=100, ttl=5)

    async def on_connect(self):
        """After connect, join channels and start consumer."""
        await super().on_connect()
        self._ready = False
        logger.info("IRC connected to {}", self._server)
        for channel in self._channels:
            await self.join(channel)
        await self._ensure_channels_permanent()
        self._consumer_task = asyncio.create_task(self._consume_outbound())
        # Fallback: if no PONG within 10s, mark ready anyway (some servers don't echo PING)
        asyncio.create_task(self._ready_fallback())  # noqa: RUF006

    async def _ensure_channels_permanent(self) -> None:
        """OPER up and set +P (permanent) on bridged channels so they persist when empty."""
        oper_password = os.environ.get("BRIDGE_IRC_OPER_PASSWORD", "").strip()
        if not oper_password:
            return
        oper_name = "atl-bridge"  # Must match oper block in UnrealIRCd
        try:
            await self.rawmsg("OPER", oper_name, oper_password)
            await asyncio.sleep(1)  # Allow server to process OPER
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
        """After 005 ISUPPORT, send PING ready for ready detection."""
        await super().on_raw_005(message)
        await self.rawmsg("PING", "ready")

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

    async def on_raw_pong(self, message) -> None:
        """Mark ready when we receive PONG ready (echo of our PING)."""
        await super().on_raw_pong(message)
        params = getattr(message, "params", [])
        if params and "ready" in (str(p) for p in params):
            self._ready = True
            logger.debug("IRC ready (PONG received)")

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

    async def on_kick(self, channel: str, target: str, by: str, reason: str | None = None) -> None:
        """Handle KICK; rejoin if we were kicked and not banned."""
        await super().on_kick(channel, target, by, reason or "")
        if not self._auto_rejoin:
            return
        # Rejoin if we (our nick) were kicked
        if target.lower() != self.nickname.lower():
            return
        if reason and "ban" in reason.lower():
            logger.warning("Not rejoining {} (ban detected)", channel)
            return
        await asyncio.sleep(self._rejoin_delay)
        await self.join(channel)
        logger.info("Rejoined {} after KICK", channel)

    async def on_disconnect(self, expected: bool) -> None:
        """Handle disconnect; rejoin channels on reconnect."""
        await super().on_disconnect(expected)
        self._ready = False

    async def on_message(self, target, source, message):
        """Handle channel message."""
        await super().on_message(target, source, message)
        if not self._ready:
            return
        if not target.startswith("#"):
            return

        mapping = self._router.get_mapping_for_irc(self._server, target)
        if not mapping:
            return

        # Extract msgid and reply from IRCv3 tags
        msgid = None
        reply_to = None
        tags = {}
        if hasattr(self, "_message_tags") and self._message_tags:
            tags = self._message_tags
            msgid = tags.get("msgid")
            reply_to = tags.get("+draft/reply")

        message_id = msgid or f"irc:{self._server}:{target}:{source}:{id(message)}"

        # Resolve reply_to to Discord message ID if available
        discord_reply_to = None
        if reply_to:
            discord_reply_to = self._msgid_tracker.get_discord_id(reply_to)

        # If this is our echo (from bridge), correlate with pending send for msgid tracking
        # RELAYMSG: server tags with draft/relaymsg=our_nick; source is spoofed nick
        # Puppets: plain PRIVMSG from our puppets; main connection receives and must skip
        # Fallback: relaymsg tag may be missing (e.g. via irc-services); check recent sends
        relayed_by_us = tags.get("draft/relaymsg") == self.nickname or tags.get("relaymsg") == self.nickname
        from_puppet = self._puppet_nick_check is not None and self._puppet_nick_check(source)
        from_recent_relaymsg = (self._server, target, source) in self._recent_relaymsg_sends
        if source == self.nickname or relayed_by_us or from_puppet or from_recent_relaymsg:
            if msgid:
                try:
                    discord_id = self._pending_sends.get_nowait()
                    self._msgid_tracker.store(msgid, discord_id)  # irc_msgid, discord_id
                    logger.debug("IRC: stored msgid {} -> {} for REDACT/edit correlation", msgid, discord_id)
                except asyncio.QueueEmpty:
                    logger.debug(
                        "IRC: RELAYMSG echo had msgid {} but no pending_send (queue empty); cannot correlate",
                        msgid,
                    )
            elif relayed_by_us or from_recent_relaymsg:
                logger.info(
                    "IRC: RELAYMSG echo received for {} in {} but no msgid tag (UnrealIRCd message-ids may not add msgid to relaymsg)",
                    source,
                    target,
                )
                logger.debug(
                    "IRC: RELAYMSG echo tags={} (empty => server may not send tags or message-tags cap not negotiated)",
                    tags,
                )
            return  # Skip publishing our own echoed messages to prevent doubling

        if msgid:
            logger.debug("IRC: external message with msgid={} from {}", msgid, source)

        _, evt = message_in(
            origin="irc",
            channel_id=mapping.discord_channel_id,
            author_id=source,
            author_display=source,
            content=message,
            message_id=message_id,
            reply_to_id=discord_reply_to,
            is_action=False,
            raw={"tags": tags, "irc_msgid": msgid, "irc_reply_to": reply_to},
        )
        logger.info("IRC message bridged: channel={} author={}", target, source)
        self._bus.publish("irc", evt)

    async def on_ctcp_action(self, by, target, message):
        """Handle /me action."""
        await super().on_ctcp_action(by, target, message)
        if not target.startswith("#"):
            return

        mapping = self._router.get_mapping_for_irc(self._server, target)
        if not mapping:
            return

        if by == self.nickname:
            return  # Skip our own /me echo

        content = f"* {by} {message}"
        _, evt = message_in(
            origin="irc",
            channel_id=mapping.discord_channel_id,
            author_id=by,
            author_display=by,
            content=content,
            message_id=f"irc:{self._server}:{target}:{by}:{id(message)}",
            is_action=True,
        )
        logger.info("IRC action bridged: channel={} author={}", target, by)
        self._bus.publish("irc", evt)

    async def on_raw_tagmsg(self, message) -> None:
        """Handle IRC TAGMSG with +draft/react, +draft/unreact, or +typing; publish for Relay."""
        if not self._ready:
            return
        params = getattr(message, "params", [])
        if not params:
            return
        target = params[0]
        if not target.startswith("#"):
            return
        mapping = self._router.get_mapping_for_irc(self._server, target)
        if not mapping:
            return

        tags = getattr(message, "tags", {}) or {}
        reply_to = tags.get("+draft/reply")
        react = tags.get("+draft/react")
        unreact = tags.get("+draft/unreact")
        typing_val = tags.get("typing")

        source = getattr(message, "source", "") or ""
        nick = source.split("!")[0] if "!" in source else source

        if react and reply_to:
            # Add reaction
            if nick == self.nickname:
                return  # Skip our own echo
            discord_id = self._msgid_tracker.get_discord_id(reply_to)
            if discord_id:
                from bridge.events import reaction_in

                msgid = tags.get("msgid")
                if msgid:
                    self._reaction_tracker.store_incoming(msgid, discord_id, react, nick)
                _, evt = reaction_in(
                    origin="irc",
                    channel_id=f"{self._server}/{target}",
                    message_id=discord_id,
                    emoji=react,
                    author_id=nick,
                    author_display=nick,
                )
                logger.info("IRC reaction bridged: channel={} author={} emoji={}", target, nick, react)
                self._bus.publish("irc", evt)
        elif unreact and reply_to:
            # Remove reaction (IRCv3 +draft/unreact)
            if nick == self.nickname:
                return  # Skip our own echo
            discord_id = self._msgid_tracker.get_discord_id(reply_to)
            if discord_id:
                from bridge.events import reaction_in

                _, evt = reaction_in(
                    origin="irc",
                    channel_id=f"{self._server}/{target}",
                    message_id=discord_id,
                    emoji=unreact,
                    author_id=nick,
                    author_display=nick,
                    raw={"is_remove": True},
                )
                logger.info("IRC reaction removal bridged: channel={} author={} emoji={}", target, nick, unreact)
                self._bus.publish("irc", evt)
        elif typing_val == "active":
            from bridge.events import typing_in

            _, evt = typing_in(
                origin="irc",
                channel_id=f"{self._server}/{target}",
                user_id=nick or "unknown",
            )
            self._bus.publish("irc", evt)

    async def on_raw_redact(self, message) -> None:
        """Handle IRC REDACT; publish MessageDelete or ReactionIn (removal) for Relay."""
        params = getattr(message, "params", [])
        if len(params) < 2:
            return
        target, irc_msgid = params[0], params[1]
        logger.debug("IRC: received REDACT target={} msgid={}", target, irc_msgid)
        if not target.startswith("#"):
            return
        mapping = self._router.get_mapping_for_irc(self._server, target)
        if not mapping:
            return

        # REDACT on reaction TAGMSG → reaction removal
        reaction_key = self._reaction_tracker.get_reaction_key(irc_msgid)
        if reaction_key:
            discord_id, emoji, author_id = reaction_key
            source = getattr(message, "source", "") or ""
            nick = source.split("!")[0] if "!" in source else source
            from bridge.events import reaction_in

            _, evt = reaction_in(
                origin="irc",
                channel_id=f"{self._server}/{target}",
                message_id=discord_id,
                emoji=emoji,
                author_id=nick or author_id,
                author_display=nick or author_id,
                raw={"is_remove": True},
            )
            logger.info("IRC REDACT (reaction) bridged: channel={} emoji={}", target, emoji)
            self._bus.publish("irc", evt)
            return

        discord_id = self._msgid_tracker.get_discord_id(irc_msgid)
        if not discord_id:
            logger.debug(
                "No Discord msgid for IRC REDACT {}; skip (msgid never stored or expired)",
                irc_msgid,
            )
            return
        source = getattr(message, "source", "") or ""
        nick = source.split("!")[0] if "!" in source else source
        from bridge.events import message_delete

        _, evt = message_delete(
            origin="irc",
            channel_id=f"{self._server}/{target}",
            message_id=discord_id,
            author_id=nick,
            author_display=nick,
        )
        logger.info("IRC REDACT (message) bridged: channel={} msgid={}", target, irc_msgid)
        self._bus.publish("irc", evt)

    async def on_raw_chghost(self, message):
        """Handle CHGHOST: user changed username/hostname."""
        # :nick!old_user@old_host CHGHOST new_user new_host
        if len(message.params) >= 2:
            nick = message.source
            new_user = message.params[0]
            new_host = message.params[1]
            logger.debug("IRC CHGHOST: {} -> {}@{}", nick, new_user, new_host)

    async def on_raw_setname(self, message):
        """Handle SETNAME: user changed realname."""
        # :nick!user@host SETNAME :new realname
        if message.params:
            nick = message.source
            new_realname = message.params[0]
            logger.debug("IRC SETNAME: {} -> {}", nick, new_realname)

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

    async def on_capability_draft_relaymsg_available(self, value):
        """Request draft/relaymsg for stateless bridging."""
        return True

    async def on_capability_overdrivenetworks_com_relaymsg_available(self, value):
        """Request overdrivenetworks.com/relaymsg (alternate relaymsg cap name)."""
        return True

    def _has_relaymsg(self) -> bool:
        """Check if RELAYMSG capability was negotiated."""
        caps = getattr(self, "_capabilities", {})
        return bool(caps.get("draft/relaymsg") or caps.get("overdrivenetworks.com/relaymsg"))

    def _sanitize_relaymsg_nick(self, nick: str) -> str:
        """Sanitize nick for RELAYMSG: replace invalid chars with '-'.
        When irc_relaymsg_clean_nicks: no /d suffix (server allows clean nicks).
        Otherwise: append /d (Valware relaymsg requires '/' in nick)."""
        invalid = " \t\n\r!+%@&#$:'\"?*,."
        out = "".join("-" if c in invalid else c for c in nick)
        out = (out or "user")[:32]
        if "/" not in out and not cfg.irc_relaymsg_clean_nicks:
            out = f"{out}/d"
        return out

    async def _consume_outbound(self):
        """Consume outbound message queue with token bucket throttling."""
        while True:
            try:
                evt = await self._outbound.get()
                # Wait for token before sending (flood control)
                wait = self._throttle.acquire()
                if wait > 0:
                    await asyncio.sleep(wait)
                self._throttle.use_token()  # Consume (guaranteed after acquire wait)
                await self._send_message(evt)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("IRC send failed: {}", exc)

    async def _send_message(self, evt: MessageOut):
        """Send message to IRC. Uses RELAYMSG when available (stateless bridging)."""
        mapping = self._router.get_mapping_for_discord(evt.channel_id)
        if not mapping or not mapping.irc:
            logger.warning("IRC send skipped: no mapping for channel {}", evt.channel_id)
            return

        target = mapping.irc.channel
        chunks = split_irc_message(evt.content, max_bytes=450)

        # Spoofed nick for RELAYMSG: display/discord (Valware requires '/' in nick)
        display = (evt.author_display or evt.author_id or "user").strip()
        spoofed_nick = self._sanitize_relaymsg_nick(display)

        use_relaymsg = self._has_relaymsg()

        # Add reply tag if replying to a message (only on first chunk)
        reply_tags = None
        if evt.reply_to_id:
            irc_msgid = self._msgid_tracker.get_irc_msgid(evt.reply_to_id)
            if irc_msgid:
                reply_tags = {"+draft/reply": irc_msgid}

        for i, chunk in enumerate(chunks):
            if use_relaymsg:
                # RELAYMSG #channel spoofed_nick :message
                if reply_tags and i == 0:
                    await self.rawmsg("RELAYMSG", target, spoofed_nick, chunk, tags=reply_tags)
                else:
                    await self.rawmsg("RELAYMSG", target, spoofed_nick, chunk)
            else:
                tags = reply_tags if i == 0 else None
                if tags:
                    await self.rawmsg("PRIVMSG", target, chunk, tags=tags)
                else:
                    await self.message(target, chunk)
            if i == 0:
                if use_relaymsg:
                    logger.info("IRC: sent RELAYMSG to {} as {}", target, spoofed_nick)
                    self._recent_relaymsg_sends[(self._server, target, spoofed_nick)] = None
                else:
                    logger.info("IRC: sent PRIVMSG to {} as {}", target, spoofed_nick)
            # Only store mapping for first chunk (echo will have msgid)
            if i == 0:
                self._pending_sends.put_nowait(evt.message_id)
                logger.debug(
                    "IRC: queued pending_send discord_id={} for echo correlation",
                    evt.message_id,
                )

    def queue_message(self, evt: MessageOut):
        """Queue outbound message."""
        logger.info("IRC: queued message for channel={}", evt.channel_id)
        self._outbound.put_nowait(evt)

    async def disconnect(self, expected=True):
        """Disconnect and cleanup."""
        if self._consumer_task:
            self._consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._consumer_task
        await super().disconnect(expected)


class IRCAdapter:
    """IRC adapter: pydle-based with IRCv3 support."""

    def __init__(
        self,
        bus: Bus,
        router: ChannelRouter,
        identity_resolver: IdentityResolver | None,
    ):
        self._bus = bus
        self._router = router
        self._identity = identity_resolver
        self._client: IRCClient | None = None
        self._task: asyncio.Task | None = None
        self._puppet_manager: IRCPuppetManager | None = None
        self._puppet_tasks: set[asyncio.Task] = set()
        self._msgid_tracker = MessageIDTracker(ttl_seconds=3600)
        self._reaction_tracker = ReactionTracker(ttl_seconds=3600)

    @property
    def name(self) -> str:
        return "irc"

    def accept_event(self, source: str, evt: object) -> bool:
        """Accept MessageOut, MessageDeleteOut, ReactionOut, or TypingOut targeting IRC."""
        if isinstance(evt, MessageOut) and evt.target_origin == "irc":
            return True
        if isinstance(evt, MessageDeleteOut) and evt.target_origin == "irc":
            return True
        if isinstance(evt, ReactionOut) and evt.target_origin == "irc":
            return True
        return isinstance(evt, TypingOut) and evt.target_origin == "irc"

    def push_event(self, source: str, evt: object) -> None:
        """Queue MessageOut, MessageDeleteOut, or ReactionOut for IRC send."""
        if isinstance(evt, MessageDeleteOut) and evt.target_origin == "irc":
            if self._client:
                logger.debug(
                    "IRC: received MessageDeleteOut channel={} message_id={}",
                    evt.channel_id,
                    evt.message_id,
                )
                asyncio.create_task(self._send_redact(evt))  # noqa: RUF006
            return
        if isinstance(evt, ReactionOut) and evt.target_origin == "irc":
            if self._client:
                asyncio.create_task(self._send_reaction(evt))  # noqa: RUF006
            return
        if isinstance(evt, TypingOut) and evt.target_origin == "irc":
            if self._client:
                asyncio.create_task(self._send_typing(evt))  # noqa: RUF006
            return
        if isinstance(evt, MessageOut):
            # Use puppet if identity available, otherwise main connection
            if self._identity and self._puppet_manager:
                task = asyncio.create_task(self._send_via_puppet(evt))
                self._puppet_tasks.add(task)
                task.add_done_callback(self._puppet_tasks.discard)
            elif self._client:
                self._client.queue_message(evt)
            else:
                logger.warning("IRC MessageOut dropped: no client (channel={})", evt.channel_id)

    async def _send_reaction(self, evt: ReactionOut) -> None:
        """Send IRC TAGMSG with +draft/react for add, or +draft/unreact for removal (IRCv3 spec)."""
        if not self._client:
            return
        is_remove = evt.raw.get("is_remove", False)
        mapping = self._router.get_mapping_for_discord(evt.channel_id)
        if not mapping or not mapping.irc:
            return
        target = mapping.irc.channel

        irc_msgid = self._msgid_tracker.get_irc_msgid(evt.message_id)
        if not irc_msgid:
            logger.debug("No IRC msgid for reaction on {}; skip", evt.message_id)
            return

        if is_remove:
            try:
                await self._client.rawmsg(
                    "TAGMSG",
                    target,
                    tags={"+draft/reply": irc_msgid, "+draft/unreact": evt.emoji},
                )
                logger.info("IRC: sent reaction removal {} on message {}", evt.emoji, evt.message_id)
            except Exception as exc:
                logger.exception("Reaction unreact TAGMSG failed: {}", exc)
            return

        # Add reaction
        try:
            await self._client.rawmsg(
                "TAGMSG",
                target,
                tags={"+draft/reply": irc_msgid, "+draft/react": evt.emoji},
            )
            logger.info("IRC: sent reaction {} to channel {}", evt.emoji, target)
        except Exception as exc:
            logger.exception("Reaction TAGMSG failed: {}", exc)

    async def _send_typing(self, evt: TypingOut) -> None:
        """Send IRC TAGMSG with +typing=active for Discord typing (throttled 3s)."""
        if not self._client:
            return
        import time

        now = time.time()
        last = getattr(self._client, "_typing_last", 0)
        if now - last < 3:
            return
        self._client._typing_last = now

        mapping = self._router.get_mapping_for_discord(evt.channel_id)
        if not mapping or not mapping.irc:
            return
        target = mapping.irc.channel
        try:
            await self._client.rawmsg(
                "TAGMSG",
                target,
                tags={"typing": "active"},
            )
        except Exception as exc:
            logger.debug("Typing TAGMSG failed: {}", exc)

    async def _send_redact(self, evt: MessageDeleteOut) -> None:
        """Send REDACT to IRC when Discord message is deleted (requires draft/message-redaction)."""
        if not self._client:
            return
        if not cfg.irc_redact_enabled:
            logger.debug(
                "IRC: skipping REDACT for message {} (irc_redact_enabled=false; UnrealIRCd third/redact crashes)",
                evt.message_id,
            )
            return
        caps = getattr(self._client, "_capabilities", {})
        if not caps.get("draft/message-redaction"):
            logger.info(
                "IRC: skipping REDACT for Discord message {} (draft/message-redaction not negotiated)",
                evt.message_id,
            )
            return
        irc_msgid = self._msgid_tracker.get_irc_msgid(evt.message_id)
        if not irc_msgid:
            logger.info(
                "IRC: skipping REDACT for Discord message {} (no IRC msgid stored; echo may lack msgid tag)",
                evt.message_id,
            )
            return
        mapping = self._router.get_mapping_for_discord(evt.channel_id)
        if not mapping or not mapping.irc:
            return
        target = mapping.irc.channel
        try:
            await self._client.rawmsg("REDACT", target, irc_msgid)
            logger.info("IRC: sent REDACT for message {} to channel {}", evt.message_id, target)
            logger.debug("IRC: REDACT irc_msgid={} -> discord_id={}", irc_msgid, evt.message_id)
        except Exception as exc:
            logger.exception("REDACT failed: {}", exc)

    async def _send_via_puppet(self, evt: MessageOut):
        """Send message via puppet connection."""
        if not self._puppet_manager or not self._identity:
            return

        mapping = self._router.get_mapping_for_discord(evt.channel_id)
        if not mapping or not mapping.irc:
            return

        # Check if user has IRC identity
        has_irc = await self._identity.has_irc(evt.author_id)
        if has_irc:
            await self._puppet_manager.send_message(
                evt.author_id,
                mapping.irc.channel,
                evt.content,
                avatar_url=evt.avatar_url,
            )
        elif self._client:
            # Fallback to main connection
            self._client.queue_message(evt)

    async def start(self) -> None:
        """Start IRC connection."""
        mappings = self._router.all_mappings()
        irc_mappings = [m for m in mappings if m.irc]
        if not irc_mappings:
            logger.warning("No IRC mappings; IRC adapter disabled")
            return

        m = irc_mappings[0]
        if not m.irc:
            return

        nick = os.environ.get("BRIDGE_IRC_NICK", "atl-bridge")
        channels = list({x.irc.channel for x in irc_mappings if x.irc and x.irc.channel})

        irc_kwargs: dict = {}
        if cfg.irc_use_sasl and cfg.irc_sasl_user and cfg.irc_sasl_password:
            irc_kwargs["sasl_username"] = cfg.irc_sasl_user
            irc_kwargs["sasl_password"] = cfg.irc_sasl_password

        self._client = IRCClient(
            bus=self._bus,
            router=self._router,
            server=m.irc.server,
            nick=nick,
            channels=channels,
            msgid_tracker=self._msgid_tracker,
            reaction_tracker=self._reaction_tracker,
            throttle_limit=cfg.irc_throttle_limit,
            rejoin_delay=cfg.irc_rejoin_delay,
            auto_rejoin=cfg.irc_auto_rejoin,
            **irc_kwargs,
        )

        self._bus.register(self)

        self._task = asyncio.create_task(
            _connect_with_backoff(
                self._client,
                hostname=m.irc.server,
                port=m.irc.port,
                tls=m.irc.tls,
                tls_verify=cfg.irc_tls_verify,
            )
        )

        # Start puppet manager if identity resolver available
        if self._identity:
            idle_timeout = int(os.environ.get("IRC_PUPPET_IDLE_TIMEOUT_HOURS", "24"))
            self._puppet_manager = IRCPuppetManager(
                bus=self._bus,
                router=self._router,
                identity=self._identity,
                server=m.irc.server,
                port=m.irc.port,
                tls=m.irc.tls,
                tls_verify=cfg.irc_tls_verify,
                idle_timeout_hours=idle_timeout,
                ping_interval=cfg.irc_puppet_ping_interval,
                prejoin_commands=cfg.irc_puppet_prejoin_commands,
            )
            pm = self._puppet_manager
            await pm.start()
            logger.info("IRC puppet manager started (idle timeout: {}h)", idle_timeout)
            # Main connection receives puppet PRIVMSGs; skip to prevent Discord echo
            self._client._puppet_nick_check = lambda n, m=pm: n in m.get_puppet_nicks()

        logger.info(
            "IRC connection started: {}:{}, channels {}",
            m.irc.server,
            m.irc.port,
            channels,
        )

    async def stop(self) -> None:
        """Stop IRC connection."""
        self._bus.unregister(self)
        if self._puppet_manager:
            await self._puppet_manager.stop()
        if self._client:
            await self._client.disconnect()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._client = None
        self._task = None
        self._puppet_manager = None
