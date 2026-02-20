"""IRC adapter: pydle-based with IRCv3 support."""

from __future__ import annotations

import asyncio
import contextlib
import os
import random
from typing import TYPE_CHECKING, ClassVar

import pydle
from loguru import logger

from bridge.adapters.irc_msgid import MessageIDTracker
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
) -> None:
    """Connect with exponential backoff and jitter on failure; reconnect on disconnect."""
    attempt = 0
    while True:
        try:
            await client.connect(hostname=hostname, port=port, tls=tls)
            # connect() returns when disconnected; reconnect with backoff
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
    }

    def __init__(
        self,
        bus: Bus,
        router: ChannelRouter,
        server: str,
        nick: str,
        channels: list[str],
        msgid_tracker: MessageIDTracker,
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
        self._throttle = TokenBucket(limit=throttle_limit, refill_rate=float(throttle_limit))
        self._rejoin_delay = rejoin_delay
        self._auto_rejoin = auto_rejoin
        self._ready = False
        self._pending_sends: asyncio.Queue[str] = asyncio.Queue()  # discord_id for echo correlation

    async def on_connect(self):
        """After connect, join channels and start consumer."""
        await super().on_connect()
        self._ready = False
        logger.info("IRC connected to {}", self._server)
        for channel in self._channels:
            await self.join(channel)
        self._consumer_task = asyncio.create_task(self._consume_outbound())
        # Fallback: if no PONG within 10s, mark ready anyway (some servers don't echo PING)
        asyncio.create_task(self._ready_fallback())  # noqa: RUF006

    async def _ready_fallback(self) -> None:
        await asyncio.sleep(10)
        if not self._ready:
            self._ready = True
            logger.debug("IRC ready (fallback timeout)")

    async def on_raw_005(self, message):
        """After 005 ISUPPORT, send PING ready for ready detection."""
        await super().on_raw_005(message)
        self.rawmsg("PING", "ready")

    async def on_raw_pong(self, message) -> None:
        """Mark ready when we receive PONG ready (echo of our PING)."""
        await super().on_raw_pong(message)
        params = getattr(message, "params", [])
        if params and "ready" in (str(p) for p in params):
            self._ready = True
            logger.debug("IRC ready (PONG received)")

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
        if source == self.nickname and msgid:
            try:
                discord_id = self._pending_sends.get_nowait()
                self._msgid_tracker.store(msgid, discord_id)  # irc_msgid, discord_id
            except asyncio.QueueEmpty:
                pass

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
        self._bus.publish("irc", evt)

    async def on_ctcp_action(self, by, target, message):
        """Handle /me action."""
        await super().on_ctcp_action(by, target, message)
        if not target.startswith("#"):
            return

        mapping = self._router.get_mapping_for_irc(self._server, target)
        if not mapping:
            return

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
        self._bus.publish("irc", evt)

    async def on_raw_tagmsg(self, message) -> None:
        """Handle IRC TAGMSG with +draft/react or +typing; publish for Relay."""
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
        typing_val = tags.get("typing")

        source = getattr(message, "source", "") or ""
        nick = source.split("!")[0] if "!" in source else source

        if react and reply_to:
            discord_id = self._msgid_tracker.get_discord_id(reply_to)
            if discord_id:
                from bridge.events import reaction_in

                _, evt = reaction_in(
                    origin="irc",
                    channel_id=f"{self._server}/{target}",
                    message_id=discord_id,
                    emoji=react,
                    author_id=nick,
                    author_display=nick,
                )
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
        """Handle IRC REDACT; publish MessageDelete for Relay to route to Discord."""
        params = getattr(message, "params", [])
        if len(params) < 2:
            return
        target, irc_msgid = params[0], params[1]
        if not target.startswith("#"):
            return
        mapping = self._router.get_mapping_for_irc(self._server, target)
        if not mapping:
            return
        discord_id = self._msgid_tracker.get_discord_id(irc_msgid)
        if not discord_id:
            logger.debug("No Discord msgid for IRC REDACT {}; skip", irc_msgid)
            return
        from bridge.events import message_delete

        _, evt = message_delete(
            origin="irc",
            channel_id=f"{self._server}/{target}",
            message_id=discord_id,
        )
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
        """Send message to IRC."""
        mapping = self._router.get_mapping_for_discord(evt.channel_id)
        if not mapping or not mapping.irc:
            return

        target = mapping.irc.channel
        chunks = split_irc_message(evt.content, max_bytes=450)

        # Add reply tag if replying to a message (only on first chunk)
        reply_tags = None
        if evt.reply_to_id:
            irc_msgid = self._msgid_tracker.get_irc_msgid(evt.reply_to_id)
            if irc_msgid:
                reply_tags = {"+draft/reply": irc_msgid}

        for i, chunk in enumerate(chunks):
            tags = reply_tags if i == 0 else None
            if tags:
                await self.rawmsg("PRIVMSG", target, chunk, tags=tags)
            else:
                await self.message(target, chunk)
            # Only store mapping for first chunk (echo will have msgid)
            if i == 0:
                self._pending_sends.put_nowait(evt.message_id)

    def queue_message(self, evt: MessageOut):
        """Queue outbound message."""
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

    async def _send_reaction(self, evt: ReactionOut) -> None:
        """Send IRC TAGMSG with +draft/react for Discord reaction."""
        if not self._client:
            return
        irc_msgid = self._msgid_tracker.get_irc_msgid(evt.message_id)
        if not irc_msgid:
            logger.debug("No IRC msgid for reaction on {}; skip", evt.message_id)
            return
        mapping = self._router.get_mapping_for_discord(evt.channel_id)
        if not mapping or not mapping.irc:
            return
        target = mapping.irc.channel
        try:
            await self._client.rawmsg(
                "TAGMSG",
                target,
                tags={"+draft/reply": irc_msgid, "+draft/react": evt.emoji},
            )
            logger.debug("Sent reaction {} to IRC", evt.emoji)
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
        """Send REDACT to IRC when Discord message is deleted."""
        if not self._client:
            return
        irc_msgid = self._msgid_tracker.get_irc_msgid(evt.message_id)
        if not irc_msgid:
            logger.debug("No IRC msgid for Discord message {}; skip REDACT", evt.message_id)
            return
        mapping = self._router.get_mapping_for_discord(evt.channel_id)
        if not mapping or not mapping.irc:
            return
        target = mapping.irc.channel
        try:
            await self._client.rawmsg("REDACT", target, irc_msgid)
            logger.debug("Sent REDACT for {} to IRC", evt.message_id)
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

        nick = os.environ.get("IRC_NICK", "atl-bridge")
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
                idle_timeout_hours=idle_timeout,
                ping_interval=cfg.irc_puppet_ping_interval,
                prejoin_commands=cfg.irc_puppet_prejoin_commands,
            )
            await self._puppet_manager.start()
            logger.info("IRC puppet manager started (idle timeout: {}h)", idle_timeout)

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
