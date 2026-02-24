"""Test message ordering guarantees."""

import asyncio

import pytest

from bridge.events import message_in
from bridge.gateway.router import ChannelMapping, IrcTarget, XmppTarget
from tests.harness import BridgeTestHarness


@pytest.fixture
def harness():
    """Create test harness with sample mappings."""
    mappings = [
        ChannelMapping(
            discord_channel_id="123",
            irc=IrcTarget(server="irc.libera.chat", port=6667, tls=False, channel="#test"),
            xmpp=XmppTarget(muc_jid="test@conference.example.com"),
        )
    ]
    return BridgeTestHarness(mappings)


class TestMessageOrdering:
    """Test that message order is preserved."""

    @pytest.mark.asyncio
    async def test_messages_arrive_in_send_order(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()
        num_messages = 100

        # Act
        for i in range(num_messages):
            harness.simulate_discord_message(
                channel_id="123",
                author_id="user1",
                author_display="User",
                content=f"Message {i}",
                message_id=f"msg{i}",
            )

        # Assert
        assert len(harness.irc.sent_messages) == num_messages
        for i, msg in enumerate(harness.irc.sent_messages):
            assert msg.content == f"Message {i}", f"Message {i} out of order"
            assert msg.message_id == f"msg{i}"
        await harness.stop()

    @pytest.mark.asyncio
    async def test_concurrent_messages_maintain_per_channel_order(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()

        # Act - send messages concurrently but track order per channel
        async def send_channel_messages(channel_id: str, count: int):
            for i in range(count):
                harness.simulate_discord_message(
                    channel_id=channel_id,
                    author_id="user1",
                    author_display="User",
                    content=f"Ch{channel_id}-Msg{i}",
                    message_id=f"ch{channel_id}-msg{i}",
                )
                await asyncio.sleep(0)  # Yield

        await asyncio.gather(
            send_channel_messages("123", 10),
        )

        # Assert - messages from same channel should be in order
        messages = harness.irc.sent_messages
        assert len(messages) == 10
        for i in range(10):
            assert f"Msg{i}" in messages[i].content
        await harness.stop()

    @pytest.mark.asyncio
    async def test_messages_from_different_origins_preserve_order(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()

        # Act - alternate between Discord and IRC messages
        for i in range(5):
            harness.simulate_discord_message(
                channel_id="123",
                author_id="discord_user",
                author_display="DiscordUser",
                content=f"Discord {i}",
                message_id=f"discord{i}",
            )
            harness.simulate_irc_message(
                server="irc.libera.chat",
                channel="#test",
                author_id="irc_user",
                author_display="IRCUser",
                content=f"IRC {i}",
                message_id=f"irc{i}",
            )

        # Assert
        # Discord messages should arrive at IRC in order
        irc_messages = [m for m in harness.irc.sent_messages if "Discord" in m.content]
        assert len(irc_messages) == 5
        for i, msg in enumerate(irc_messages):
            assert msg.content == f"Discord {i}"

        # IRC messages should arrive at Discord in order
        discord_messages = [m for m in harness.discord.sent_messages if "IRC" in m.content]
        assert len(discord_messages) == 5
        for i, msg in enumerate(discord_messages):
            assert msg.content == f"IRC {i}"
        await harness.stop()

    @pytest.mark.asyncio
    async def test_rapid_fire_messages_maintain_order(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()
        num_messages = 1000

        # Act - send messages as fast as possible
        for i in range(num_messages):
            harness.simulate_discord_message(
                channel_id="123",
                author_id="user1",
                author_display="User",
                content=str(i),
                message_id=f"msg{i}",
            )

        # Assert - all messages in correct order
        assert len(harness.irc.sent_messages) == num_messages
        for i, msg in enumerate(harness.irc.sent_messages):
            assert msg.content == str(i), f"Expected {i}, got {msg.content}"
        await harness.stop()

    @pytest.mark.asyncio
    async def test_message_order_with_replies(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()

        # Act - send messages with replies interspersed
        harness.simulate_discord_message(
            channel_id="123",
            author_id="user1",
            author_display="User1",
            content="Message 0",
            message_id="msg0",
        )

        _, reply1 = message_in(
            origin="discord",
            channel_id="123",
            author_id="user2",
            author_display="User2",
            content="Reply to 0",
            message_id="msg1",
            reply_to_id="msg0",
        )
        harness.bus.publish("discord", reply1)

        harness.simulate_discord_message(
            channel_id="123",
            author_id="user1",
            author_display="User1",
            content="Message 2",
            message_id="msg2",
        )

        # Assert - messages arrive in send order, not reply order
        assert len(harness.irc.sent_messages) == 3
        assert harness.irc.sent_messages[0].content == "Message 0"
        assert harness.irc.sent_messages[1].content == "Reply to 0"
        assert harness.irc.sent_messages[2].content == "Message 2"
        await harness.stop()

    @pytest.mark.asyncio
    async def test_message_order_across_adapter_restarts(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()

        # Act - send messages, unregister adapter, send more, re-register
        harness.simulate_discord_message(
            channel_id="123",
            author_id="user1",
            author_display="User",
            content="Before unregister",
            message_id="msg1",
        )

        harness.bus.unregister(harness.irc)

        harness.simulate_discord_message(
            channel_id="123",
            author_id="user1",
            author_display="User",
            content="During unregister",
            message_id="msg2",
        )

        harness.bus.register(harness.irc)

        harness.simulate_discord_message(
            channel_id="123",
            author_id="user1",
            author_display="User",
            content="After re-register",
            message_id="msg3",
        )

        # Assert - only messages sent while registered are received
        assert len(harness.irc.sent_messages) == 2
        assert harness.irc.sent_messages[0].content == "Before unregister"
        assert harness.irc.sent_messages[1].content == "After re-register"
        await harness.stop()
