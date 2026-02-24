"""Test error handling and exception scenarios."""

from unittest.mock import AsyncMock

import httpx
import pytest

from bridge.events import message_in
from bridge.gateway.bus import Bus
from bridge.gateway.relay import Relay
from bridge.gateway.router import ChannelRouter
from bridge.identity import IdentityResolver, PortalClient
from tests.mocks import MockIRCAdapter


class TestPortalClientErrors:
    """Test Portal API client error handling."""

    @pytest.mark.asyncio
    async def test_resolver_returns_none_when_client_returns_none(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.return_value = None
        resolver = IdentityResolver(client=mock_client)

        # Act
        result = await resolver.discord_to_irc("123")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_resolver_propagates_client_exceptions(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.TimeoutException("Timeout")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.TimeoutException):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_resolver_handles_missing_fields_in_response(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.return_value = {"discord_id": "123"}  # Missing irc_nick
        resolver = IdentityResolver(client=mock_client)

        # Act
        result = await resolver.discord_to_irc("123")

        # Assert
        assert result is None  # Returns None when field is missing

    @pytest.mark.asyncio
    async def test_resolver_handles_malformed_response(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.return_value = {"unexpected": "data"}
        resolver = IdentityResolver(client=mock_client)

        # Act
        result = await resolver.discord_to_irc("123")

        # Assert
        assert result is None


class TestConfigErrors:
    """Test configuration error handling."""

    def test_invalid_yaml_raises_error(self):
        # Arrange
        import tempfile

        import yaml

        from bridge.config import load_config

        # Act & Assert
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: syntax:")
            path = f.name

        with pytest.raises((ValueError, KeyError, TypeError, yaml.YAMLError)):
            load_config(path)

    def test_missing_config_file_returns_empty(self):
        # Arrange
        from bridge.config import load_config

        # Act
        result = load_config("/nonexistent/config.yaml")

        # Assert
        assert result == {}

    def test_router_handles_malformed_mappings(self):
        # Arrange
        router = ChannelRouter()
        config = {
            "mappings": [
                "not a dict",
                {"discord_channel_id": ""},  # Empty ID
                {"no_discord_id": "value"},  # Missing required field
                {"discord_channel_id": "123"},  # Valid
            ]
        }

        # Act
        router.load_from_config(config)

        # Assert
        assert len(router.all_mappings()) == 1


class TestEventBusErrors:
    """Test event bus error handling."""

    def test_bus_continues_after_target_exception(self):
        # Arrange
        bus = Bus()

        class FailingTarget:
            def accept_event(self, source, evt):
                return True

            def push_event(self, source, evt):
                raise RuntimeError("Target failed")

        class WorkingTarget:
            def __init__(self):
                self.received = []

            def accept_event(self, source, evt):
                return True

            def push_event(self, source, evt):
                self.received.append(evt)

        failing = FailingTarget()
        working = WorkingTarget()
        bus.register(failing)
        bus.register(working)

        # Act
        _, evt = message_in("test", "ch1", "u1", "User", "Test", "msg1")
        bus.publish("test", evt)

        # Assert - working target still receives event despite failing target
        assert len(working.received) == 1

    def test_unregister_nonexistent_target_safe(self):
        # Arrange
        bus = Bus()

        class DummyTarget:
            def accept_event(self, source, evt):
                return True

            def push_event(self, source, evt):
                pass

        target = DummyTarget()

        # Act & Assert - should not raise
        bus.unregister(target)


class TestRelayErrors:
    """Test relay error handling."""

    def test_relay_handles_unmapped_channel(self):
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        config = {"mappings": [{"discord_channel_id": "123"}]}
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockIRCAdapter()
        bus.register(relay)
        bus.register(irc_adapter)

        # Act - send to unmapped channel
        _, evt = message_in("discord", "999", "u1", "User", "Test", "msg1")
        bus.publish("discord", evt)

        # Assert - no messages sent
        assert len(irc_adapter.sent_messages) == 0

    def test_relay_handles_malformed_irc_channel_id(self):
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {
                        "server": "irc.libera.chat",
                        "channel": "#test",
                        "port": 6667,
                        "tls": False,
                    },
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        from tests.mocks import MockDiscordAdapter

        discord_adapter = MockDiscordAdapter()
        bus.register(relay)
        bus.register(discord_adapter)

        # Act - send with malformed IRC channel ID (no "/")
        _, evt = message_in("irc", "malformed", "u1", "User", "Test", "msg1")
        bus.publish("irc", evt)

        # Assert - no messages sent due to malformed ID
        assert len(discord_adapter.sent_messages) == 0

    def test_relay_ignores_non_message_events(self):
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        relay = Relay(bus, router)
        irc_adapter = MockIRCAdapter()
        bus.register(relay)
        bus.register(irc_adapter)

        # Act - send non-MessageIn event
        from bridge.events import Join

        join_evt = Join(origin="discord", channel_id="123", user_id="u1", display="User")
        bus.publish("discord", join_evt)

        # Assert - relay ignores non-MessageIn events
        assert len(irc_adapter.sent_messages) == 0


class TestAdapterErrors:
    """Test adapter error scenarios."""

    def test_adapter_handles_empty_message_content(self):
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {
                        "server": "irc.libera.chat",
                        "channel": "#test",
                        "port": 6667,
                        "tls": False,
                    },
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockIRCAdapter()
        bus.register(relay)
        bus.register(irc_adapter)

        # Act - send empty message
        _, evt = message_in("discord", "123", "u1", "User", "", "msg1")
        bus.publish("discord", evt)

        # Assert - message still sent (empty content is valid)
        assert len(irc_adapter.sent_messages) == 1
        assert irc_adapter.sent_messages[0].content == ""

    def test_adapter_handles_none_values(self):
        # Arrange
        from bridge.events import MessageOut

        # Act & Assert - should not raise
        msg = MessageOut(
            target_origin="irc",
            channel_id="123",
            author_id="u1",
            author_display="User",
            content="Test",
            message_id="msg1",
            reply_to_id=None,  # None is valid
        )
        assert msg.reply_to_id is None
