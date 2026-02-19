"""IRC adapter: pydle-based with IRCv3 support."""

from __future__ import annotations

import asyncio
import contextlib
import os
from typing import TYPE_CHECKING, ClassVar

import pydle
from loguru import logger

from bridge.adapters.irc_msgid import MessageIDTracker
from bridge.adapters.irc_puppet import IRCPuppetManager
from bridge.events import MessageOut, message_in
from bridge.gateway import Bus, ChannelRouter

if TYPE_CHECKING:
    from bridge.identity import IdentityResolver


class IRCClient(pydle.Client):
    """Pydle IRC client with IRCv3 capabilities."""

    CAPABILITIES: ClassVar[set[str]] = {
        "message-tags",
        "msgid",
        "account-notify",
        "extended-join",
        "server-time",
        "draft/reply",
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

    async def on_connect(self):
        """After connect, join channels and start consumer."""
        await super().on_connect()
        logger.info("IRC connected to {}", self._server)
        for channel in self._channels:
            await self.join(channel)
        self._consumer_task = asyncio.create_task(self._consume_outbound())

    async def on_message(self, target, source, message):
        """Handle channel message."""
        await super().on_message(target, source, message)
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
        """Consume outbound message queue."""
        while True:
            try:
                evt = await self._outbound.get()
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
        content = evt.content[:400]  # IRC length limit

        # Add reply tag if replying to a message
        if evt.reply_to_id:
            irc_msgid = self._msgid_tracker.get_irc_msgid(evt.reply_to_id)
            if irc_msgid:
                # Send with +draft/reply tag
                await self.rawmsg("TAGMSG", target, tags={"+draft/reply": irc_msgid})

        await self.message(target, content)

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
        """Accept MessageOut targeting IRC."""
        return isinstance(evt, MessageOut) and evt.target_origin == "irc"

    def push_event(self, source: str, evt: object) -> None:
        """Queue MessageOut for IRC send."""
        if isinstance(evt, MessageOut):
            # Use puppet if identity available, otherwise main connection
            if self._identity and self._puppet_manager:
                task = asyncio.create_task(self._send_via_puppet(evt))
                self._puppet_tasks.add(task)
                task.add_done_callback(self._puppet_tasks.discard)
            elif self._client:
                self._client.queue_message(evt)

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

        self._client = IRCClient(
            bus=self._bus,
            router=self._router,
            server=m.irc.server,
            nick=nick,
            channels=channels,
            msgid_tracker=self._msgid_tracker,
        )

        self._bus.register(self)

        self._task = asyncio.create_task(
            self._client.connect(
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
