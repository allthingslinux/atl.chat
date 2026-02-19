"""Performance and load tests."""

import asyncio
import time

import pytest

from bridge.events import message_in
from bridge.gateway.bus import Bus
from bridge.gateway.relay import Relay
from bridge.gateway.router import ChannelRouter
from tests.mocks import MockIRCAdapter


class TestPerformance:
    """Performance and load tests."""

    def test_message_throughput(self):
        """Test message processing throughput."""
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
        start = time.time()
        num_messages = 1000
        for i in range(num_messages):
            _, evt = message_in("discord", "123", f"u{i}", f"User{i}", f"Message {i}", f"msg{i}")
            bus.publish("discord", evt)
        elapsed = time.time() - start

        # Assert
        assert len(irc_adapter.sent_messages) == num_messages
        messages_per_second = num_messages / elapsed
        assert messages_per_second > 1000  # Should process >1000 msg/s

    @pytest.mark.asyncio
    async def test_concurrent_channel_load(self):
        """Test handling messages across multiple channels concurrently."""
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": f"{i}",
                    "irc": {"server": "irc.libera.chat", "channel": f"#test{i}", "port": 6667, "tls": False},
                }
                for i in range(10)
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockIRCAdapter()
        bus.register(relay)
        bus.register(irc_adapter)

        # Act
        async def send_messages(channel_id, count):
            for i in range(count):
                _, evt = message_in("discord", channel_id, f"u{i}", f"User{i}", f"Msg {i}", f"msg{i}")
                bus.publish("discord", evt)
                await asyncio.sleep(0)  # Yield to event loop

        start = time.time()
        await asyncio.gather(*[send_messages(str(i), 100) for i in range(10)])
        elapsed = time.time() - start

        # Assert
        assert len(irc_adapter.sent_messages) == 1000
        assert elapsed < 1.0  # Should complete in under 1 second

    def test_memory_efficiency_large_messages(self):
        """Test memory handling with large message content."""
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

        # Act - send messages with large content
        large_content = "A" * 100000  # 100KB message
        for i in range(100):
            _, evt = message_in("discord", "123", f"u{i}", f"User{i}", large_content, f"msg{i}")
            bus.publish("discord", evt)

        # Assert
        assert len(irc_adapter.sent_messages) == 100
        assert all(len(msg.content) == 100000 for msg in irc_adapter.sent_messages)

    def test_adapter_registration_performance(self):
        """Test performance of registering/unregistering many adapters."""
        # Arrange
        bus = Bus()
        adapters = [MockIRCAdapter() for _ in range(1000)]

        # Act - register
        start = time.time()
        for adapter in adapters:
            bus.register(adapter)
        register_time = time.time() - start

        # Act - unregister
        start = time.time()
        for adapter in adapters:
            bus.unregister(adapter)
        unregister_time = time.time() - start

        # Assert
        assert register_time < 0.1  # Should be fast
        assert unregister_time < 0.1
