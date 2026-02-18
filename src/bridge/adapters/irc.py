"""IRC adapter: main connection, join channels, emit MessageIn; queue for outbound."""

from __future__ import annotations

import contextlib
import queue
import ssl
import threading
from typing import TYPE_CHECKING

import irc.client
import irc.connection
from loguru import logger

from bridge.events import MessageOut, message_in
from bridge.gateway import Bus, ChannelRouter

if TYPE_CHECKING:
    from bridge.identity import IdentityResolver


class IRCBot(irc.client.SimpleIRCClient):
    """IRC client: connects, joins bridged channels, emits MessageIn."""

    def __init__(
        self,
        bus: Bus,
        router: ChannelRouter,
        server: str,
        port: int,
        nick: str,
        use_ssl: bool,
        channels: list[str],
        outbound_queue: queue.Queue[MessageOut],
    ) -> None:
        super().__init__()
        self._bus = bus
        self._router = router
        self._server = server
        self._port = port
        self._nick = nick
        self._use_ssl = use_ssl
        self._channels = channels
        self._outbound = outbound_queue

    def on_welcome(self, connection: irc.client.ServerConnection, event: irc.client.Event) -> None:
        """After connect, join channels and schedule outbound consumer."""
        for ch in self._channels:
            connection.join(ch)
        # Schedule periodic drain of outbound queue (runs in reactor thread)
        self.reactor.scheduler.execute_every(period=0.5, func=self._drain_outbound)

    def _drain_outbound(self) -> None:
        """Drain outbound queue and send to IRC (runs in reactor thread)."""
        sent = 0
        while sent < 5:  # Batch limit
            try:
                evt = self._outbound.get_nowait()
            except queue.Empty:
                break
            try:
                mapping = self._router.get_mapping_for_discord(evt.channel_id)
                if mapping and mapping.irc:
                    target = mapping.irc.channel
                    content = evt.content[:400]  # IRC length limit
                    self.connection.privmsg(target, content)
                    sent += 1
            except Exception as exc:
                logger.exception("IRC send failed: {}", exc)

    def on_pubmsg(self, connection: irc.client.ServerConnection, event: irc.client.Event) -> None:
        """Handle channel message."""
        nick = event.source.nick
        channel = event.target
        text = event.arguments[0] if event.arguments else ""

        mapping = self._router.get_mapping_for_irc(self._server, channel)
        if not mapping:
            return

        discord_channel_id = mapping.discord_channel_id
        _, evt = message_in(
            origin="irc",
            channel_id=discord_channel_id,
            author_id=nick,
            author_display=nick,
            content=text,
            message_id=f"irc:{self._server}:{channel}:{nick}:{id(event)}",
            is_action=False,
        )
        self._bus.publish("irc", evt)

    def on_action(self, connection: irc.client.ServerConnection, event: irc.client.Event) -> None:
        """Handle /me action."""
        nick = event.source.nick
        channel = event.target
        text = event.arguments[0] if event.arguments else ""
        content = f"* {nick} {text}"

        mapping = self._router.get_mapping_for_irc(self._server, channel)
        if not mapping:
            return

        _, evt = message_in(
            origin="irc",
            channel_id=mapping.discord_channel_id,
            author_id=nick,
            author_display=nick,
            content=content,
            message_id=f"irc:{self._server}:{channel}:{nick}:{id(event)}",
            is_action=True,
        )
        self._bus.publish("irc", evt)

    def run(self) -> None:
        """Connect and run reactor."""
        if self._use_ssl:
            ctx = ssl.create_default_context()
            factory = irc.connection.Factory(
                wrapper=lambda sock: ctx.wrap_socket(sock, server_hostname=self._server)
            )
        else:
            factory = irc.connection.Factory()

        self.connection.connect(
            self._server,
            self._port,
            self._nick,
            ircname=self._nick,
            connect_factory=factory,
        )
        self.reactor.process_forever()


class IRCAdapter:
    """IRC adapter: main connection + queue for outbound."""

    def __init__(
        self,
        bus: Bus,
        router: ChannelRouter,
        identity_resolver: IdentityResolver | None,
    ) -> None:
        self._bus = bus
        self._router = router
        self._identity = identity_resolver
        self._outbound: queue.Queue[MessageOut] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._bot: IRCBot | None = None

    @property
    def name(self) -> str:
        return "irc"

    def accept_event(self, source: str, evt: object) -> bool:
        """Accept MessageOut targeting IRC."""
        return isinstance(evt, MessageOut) and evt.target_origin == "irc"

    def push_event(self, source: str, evt: object) -> None:
        """Queue MessageOut for IRC send."""
        if isinstance(evt, MessageOut):
            self._outbound.put(evt)

    async def start(self) -> None:
        """Start IRC main connection in background thread."""
        mappings = self._router.all_mappings()
        irc_mappings = [m for m in mappings if m.irc]
        if not irc_mappings:
            logger.warning("No IRC mappings; IRC adapter disabled")
            return

        # Use first IRC mapping for main connection
        m = irc_mappings[0]
        if not m.irc:
            return

        nick = _get_irc_nick()
        channels = [m.irc.channel] + [
            x.irc.channel for x in irc_mappings[1:] if x.irc and x.irc.channel
        ]
        channels = list(dict.fromkeys(channels))  # Dedupe

        self._bot = IRCBot(
            bus=self._bus,
            router=self._router,
            server=m.irc.server,
            port=m.irc.port,
            nick=nick,
            use_ssl=m.irc.tls,
            channels=channels,
            outbound_queue=self._outbound,
        )

        self._bus.register(self)
        self._thread = threading.Thread(target=self._bot.run, daemon=True)
        self._thread.start()
        logger.info(
            "IRC main connection started: {}:{}, channels {}",
            m.irc.server,
            m.irc.port,
            channels,
        )

    async def stop(self) -> None:
        """Stop IRC connection."""
        self._bus.unregister(self)
        if self._bot and self._bot.connection:
            with contextlib.suppress(Exception):
                self._bot.connection.quit("Bridge shutting down")
        self._thread = None
        self._bot = None


def _get_irc_nick() -> str:
    """Get IRC nick from env."""
    import os

    return os.environ.get("IRC_NICK", "atl-bridge")
