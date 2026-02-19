"""Test harness for bridge testing - simulates message flow without real connections."""

from __future__ import annotations

from typing import Any

from bridge.events import message_in
from bridge.gateway import Bus, ChannelRouter
from bridge.gateway.relay import Relay
from bridge.gateway.router import ChannelMapping
from tests.mocks import MockAdapter, MockDiscordAdapter, MockIRCAdapter, MockXMPPAdapter


class BridgeTestHarness:
    """Test harness for bridge - sets up bus, router, and mock adapters."""

    def __init__(self, mappings: list[ChannelMapping]) -> None:
        self.bus = Bus()
        self.router = ChannelRouter()

        # Load mappings into router
        config = {"mappings": [self._mapping_to_dict(m) for m in mappings]}
        self.router.load_from_config(config)

        # Create relay
        self.relay = Relay(self.bus, self.router)
        self.bus.register(self.relay)

        # Create mock adapters
        self.discord = MockDiscordAdapter()
        self.irc = MockIRCAdapter()
        self.xmpp = MockXMPPAdapter()

        # Register adapters
        self.bus.register(self.discord)
        self.bus.register(self.irc)
        self.bus.register(self.xmpp)

    def _mapping_to_dict(self, mapping: ChannelMapping) -> dict[str, Any]:
        """Convert ChannelMapping to config dict."""
        result: dict[str, Any] = {"discord_channel_id": mapping.discord_channel_id}
        if mapping.irc:
            result["irc"] = {
                "server": mapping.irc.server,
                "channel": mapping.irc.channel,
                "port": mapping.irc.port,
                "tls": mapping.irc.tls,
            }
        if mapping.xmpp:
            result["xmpp"] = {"muc_jid": mapping.xmpp.muc_jid}
        return result

    async def start(self) -> None:
        """Start all adapters."""
        await self.discord.start()
        await self.irc.start()
        await self.xmpp.start()

    async def stop(self) -> None:
        """Stop all adapters."""
        await self.discord.stop()
        await self.irc.stop()
        await self.xmpp.stop()

    def clear(self) -> None:
        """Clear all captured events."""
        self.discord.clear()
        self.irc.clear()
        self.xmpp.clear()

    def simulate_discord_message(
        self,
        channel_id: str,
        author_id: str,
        author_display: str,
        content: str,
        message_id: str = "msg-1",
    ) -> None:
        """Simulate a Discord message."""
        _, evt = message_in(
            origin="discord",
            channel_id=channel_id,
            author_id=author_id,
            author_display=author_display,
            content=content,
            message_id=message_id,
        )
        self.bus.publish("discord", evt)

    def simulate_irc_message(
        self,
        server: str,
        channel: str,
        author_id: str,
        author_display: str,
        content: str,
        message_id: str = "msg-1",
    ) -> None:
        """Simulate an IRC message."""
        _, evt = message_in(
            origin="irc",
            channel_id=f"{server}/{channel}",
            author_id=author_id,
            author_display=author_display,
            content=content,
            message_id=message_id,
        )
        self.bus.publish("irc", evt)

    def simulate_xmpp_message(
        self,
        channel_id: str,
        author_id: str,
        author_display: str,
        content: str,
        message_id: str = "msg-1",
    ) -> None:
        """Simulate an XMPP message."""
        _, evt = message_in(
            origin="xmpp",
            channel_id=channel_id,
            author_id=author_id,
            author_display=author_display,
            content=content,
            message_id=message_id,
        )
        self.bus.publish("xmpp", evt)

    def get_adapter(self, name: str) -> MockAdapter:
        """Get adapter by name."""
        if name == "discord":
            return self.discord
        elif name == "irc":
            return self.irc
        elif name == "xmpp":
            return self.xmpp
        else:
            raise ValueError(f"Unknown adapter: {name}")
