"""Test reply and threading functionality."""

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


class TestMessageReplies:
    """Test message reply functionality."""

    @pytest.mark.asyncio
    async def test_reply_to_message(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()

        # Act - send original message
        harness.simulate_discord_message(
            channel_id="123",
            author_id="user1",
            author_display="User1",
            content="Original message",
            message_id="msg1",
        )

        # Send reply
        _, reply_evt = message_in(
            origin="discord",
            channel_id="123",
            author_id="user2",
            author_display="User2",
            content="Reply to original",
            message_id="msg2",
            reply_to_id="msg1",
        )
        harness.bus.publish("discord", reply_evt)

        # Assert
        assert len(harness.irc.sent_messages) == 2
        reply_msg = harness.irc.sent_messages[1]
        assert reply_msg.reply_to_id == "msg1"
        assert reply_msg.content == "Reply to original"
        await harness.stop()

    @pytest.mark.asyncio
    async def test_reply_chain(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()

        # Act - create reply chain
        messages = [
            ("msg1", None, "First message"),
            ("msg2", "msg1", "Reply to first"),
            ("msg3", "msg2", "Reply to reply"),
        ]

        for msg_id, reply_to, content in messages:
            _, evt = message_in(
                origin="discord",
                channel_id="123",
                author_id="user1",
                author_display="User",
                content=content,
                message_id=msg_id,
                reply_to_id=reply_to,
            )
            harness.bus.publish("discord", evt)

        # Assert
        assert len(harness.irc.sent_messages) == 3
        assert harness.irc.sent_messages[0].reply_to_id is None
        assert harness.irc.sent_messages[1].reply_to_id == "msg1"
        assert harness.irc.sent_messages[2].reply_to_id == "msg2"
        await harness.stop()

    @pytest.mark.asyncio
    async def test_reply_from_different_platform(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()

        # Act - Discord message
        harness.simulate_discord_message(
            channel_id="123",
            author_id="discord_user",
            author_display="DiscordUser",
            content="From Discord",
            message_id="discord_msg1",
        )

        # IRC reply to Discord message
        _, reply_evt = message_in(
            origin="irc",
            channel_id="irc.libera.chat/#test",
            author_id="irc_user",
            author_display="IRCUser",
            content="Reply from IRC",
            message_id="irc_msg1",
            reply_to_id="discord_msg1",
        )
        harness.bus.publish("irc", reply_evt)

        # Assert
        assert len(harness.discord.sent_messages) == 1
        reply_msg = harness.discord.sent_messages[0]
        assert reply_msg.reply_to_id == "discord_msg1"
        await harness.stop()


class TestMessageMetadata:
    """Test message metadata preservation."""

    @pytest.mark.asyncio
    async def test_raw_data_preserved(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()
        raw_data = {"custom_field": "value", "timestamp": 1234567890}

        # Act
        _, evt = message_in(
            origin="discord",
            channel_id="123",
            author_id="user1",
            author_display="User",
            content="Test",
            message_id="msg1",
            raw=raw_data,
        )
        harness.bus.publish("discord", evt)

        # Assert
        assert len(harness.irc.sent_messages) == 1
        # Raw data is preserved in MessageIn but not necessarily in MessageOut
        await harness.stop()

    @pytest.mark.asyncio
    async def test_message_with_all_fields(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()

        # Act
        _, evt = message_in(
            origin="discord",
            channel_id="123",
            author_id="user123",
            author_display="TestUser",
            content="Complete message",
            message_id="msg-full",
            reply_to_id="msg-parent",
            is_edit=True,
            is_action=False,
            raw={"extra": "data"},
        )
        harness.bus.publish("discord", evt)

        # Assert
        assert len(harness.irc.sent_messages) == 1
        msg = harness.irc.sent_messages[0]
        assert msg.author_id == "user123"
        assert msg.author_display == "TestUser"
        assert msg.content == "Complete message"
        assert msg.message_id == "msg-full"
        assert msg.reply_to_id == "msg-parent"
        await harness.stop()
