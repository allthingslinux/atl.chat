"""Test edge cases and race conditions."""

import asyncio

import pytest

from bridge.events import message_in
from bridge.gateway.bus import Bus
from bridge.gateway.relay import Relay
from bridge.gateway.router import ChannelRouter
from tests.mocks import MockDiscordAdapter, MockIRCAdapter


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_message_content(self):
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {"server": "irc.libera.chat", "channel": "#test", "port": 6667, "tls": False},
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockIRCAdapter()
        bus.register(relay)
        bus.register(irc_adapter)

        # Act
        _, evt = message_in("discord", "123", "u1", "User", "", "msg1")
        bus.publish("discord", evt)

        # Assert
        assert len(irc_adapter.sent_messages) == 1
        assert irc_adapter.sent_messages[0].content == ""

    def test_very_long_message_content(self):
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {"server": "irc.libera.chat", "channel": "#test", "port": 6667, "tls": False},
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockIRCAdapter()
        bus.register(relay)
        bus.register(irc_adapter)

        # Act
        long_content = "A" * 10000
        _, evt = message_in("discord", "123", "u1", "User", long_content, "msg1")
        bus.publish("discord", evt)

        # Assert
        assert len(irc_adapter.sent_messages) == 1
        assert irc_adapter.sent_messages[0].content == long_content

    def test_special_characters_in_message(self):
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {"server": "irc.libera.chat", "channel": "#test", "port": 6667, "tls": False},
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockIRCAdapter()
        bus.register(relay)
        bus.register(irc_adapter)

        # Act
        special_content = "Hello 👋 @everyone #test <script>alert('xss')</script>"
        _, evt = message_in("discord", "123", "u1", "User", special_content, "msg1")
        bus.publish("discord", evt)

        # Assert
        assert len(irc_adapter.sent_messages) == 1
        assert irc_adapter.sent_messages[0].content == special_content

    def test_unicode_in_display_name(self):
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {"server": "irc.libera.chat", "channel": "#test", "port": 6667, "tls": False},
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockIRCAdapter()
        bus.register(relay)
        bus.register(irc_adapter)

        # Act
        _, evt = message_in("discord", "123", "u1", "用户名", "Hello", "msg1")
        bus.publish("discord", evt)

        # Assert
        assert len(irc_adapter.sent_messages) == 1
        assert irc_adapter.sent_messages[0].author_display == "用户名"

    def test_malformed_irc_channel_id(self):
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {"server": "irc.libera.chat", "channel": "#test", "port": 6667, "tls": False},
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        discord_adapter = MockDiscordAdapter()
        bus.register(relay)
        bus.register(discord_adapter)

        # Act - malformed channel_id without "/"
        _, evt = message_in("irc", "malformed", "u1", "User", "Hello", "msg1")
        bus.publish("irc", evt)

        # Assert - should not crash, just not route
        assert len(discord_adapter.sent_messages) == 0

    def test_multiple_adapters_same_type(self):
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {"server": "irc.libera.chat", "channel": "#test", "port": 6667, "tls": False},
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter1 = MockIRCAdapter()
        irc_adapter2 = MockIRCAdapter()
        bus.register(relay)
        bus.register(irc_adapter1)
        bus.register(irc_adapter2)

        # Act
        _, evt = message_in("discord", "123", "u1", "User", "Hello", "msg1")
        bus.publish("discord", evt)

        # Assert - both adapters receive the message
        assert len(irc_adapter1.sent_messages) == 1
        assert len(irc_adapter2.sent_messages) == 1


@pytest.mark.asyncio
class TestConcurrency:
    """Test concurrent message handling."""

    async def test_concurrent_messages_same_channel(self):
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {"server": "irc.libera.chat", "channel": "#test", "port": 6667, "tls": False},
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockIRCAdapter()
        bus.register(relay)
        bus.register(irc_adapter)

        # Act - send multiple messages concurrently
        async def send_message(i):
            _, evt = message_in("discord", "123", f"u{i}", f"User{i}", f"Message {i}", f"msg{i}")
            bus.publish("discord", evt)

        await asyncio.gather(*[send_message(i) for i in range(10)])

        # Assert - all messages received
        assert len(irc_adapter.sent_messages) == 10

    async def test_concurrent_messages_different_channels(self):
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {"server": "irc.libera.chat", "channel": "#test1", "port": 6667, "tls": False},
                },
                {
                    "discord_channel_id": "456",
                    "irc": {"server": "irc.libera.chat", "channel": "#test2", "port": 6667, "tls": False},
                },
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockIRCAdapter()
        bus.register(relay)
        bus.register(irc_adapter)

        # Act
        async def send_message(channel_id, i):
            _, evt = message_in("discord", channel_id, f"u{i}", f"User{i}", f"Message {i}", f"msg{i}")
            bus.publish("discord", evt)

        await asyncio.gather(
            *[send_message("123", i) for i in range(5)],
            *[send_message("456", i) for i in range(5, 10)],
        )

        # Assert
        assert len(irc_adapter.sent_messages) == 10

    async def test_adapter_register_unregister_during_dispatch(self):
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {"server": "irc.libera.chat", "channel": "#test", "port": 6667, "tls": False},
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockIRCAdapter()
        bus.register(relay)
        bus.register(irc_adapter)

        # Act - unregister during message flow
        _, evt = message_in("discord", "123", "u1", "User", "Message 1", "msg1")
        bus.publish("discord", evt)
        bus.unregister(irc_adapter)
        _, evt2 = message_in("discord", "123", "u1", "User", "Message 2", "msg2")
        bus.publish("discord", evt2)

        # Assert - only first message received
        assert len(irc_adapter.sent_messages) == 1
