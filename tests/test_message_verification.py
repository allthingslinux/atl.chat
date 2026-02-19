"""Test message verification and assertions."""

import pytest

from bridge.events import MessageOut, message_out
from tests.harness import BridgeTestHarness
from bridge.gateway.router import ChannelMapping, IrcTarget, XmppTarget


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


class TestMessageVerification:
    """Test message content verification."""

    @pytest.mark.asyncio
    async def test_message_content_equals(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()

        # Act
        harness.simulate_discord_message(
            channel_id="123",
            author_id="user1",
            author_display="TestUser",
            content="Hello World",
        )

        # Assert
        assert len(harness.irc.sent_messages) == 1
        assert harness.irc.sent_messages[0].content == "Hello World"
        await harness.stop()

    @pytest.mark.asyncio
    async def test_message_content_contains(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()

        # Act
        harness.simulate_discord_message(
            channel_id="123",
            author_id="user1",
            author_display="TestUser",
            content="This is a long message with keywords",
        )

        # Assert
        assert len(harness.irc.sent_messages) == 1
        assert "keywords" in harness.irc.sent_messages[0].content
        assert "long message" in harness.irc.sent_messages[0].content
        await harness.stop()

    @pytest.mark.asyncio
    async def test_no_messages_sent(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()

        # Act - don't send any messages

        # Assert
        assert len(harness.irc.sent_messages) == 0
        assert len(harness.discord.sent_messages) == 0
        assert len(harness.xmpp.sent_messages) == 0
        await harness.stop()

    @pytest.mark.asyncio
    async def test_message_author_preserved(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()

        # Act
        harness.simulate_discord_message(
            channel_id="123",
            author_id="user123",
            author_display="CoolUser",
            content="Test",
        )

        # Assert
        msg = harness.irc.sent_messages[0]
        assert msg.author_id == "user123"
        assert msg.author_display == "CoolUser"
        await harness.stop()

    @pytest.mark.asyncio
    async def test_message_id_preserved(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()

        # Act
        harness.simulate_discord_message(
            channel_id="123",
            author_id="user1",
            author_display="User",
            content="Test",
            message_id="msg-12345",
        )

        # Assert
        msg = harness.irc.sent_messages[0]
        assert msg.message_id == "msg-12345"
        await harness.stop()


class TestMessageEditing:
    """Test message editing functionality."""

    @pytest.mark.asyncio
    async def test_edited_message_flag(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()
        from bridge.events import message_in

        # Act - send edited message
        _, evt = message_in(
            origin="discord",
            channel_id="123",
            author_id="user1",
            author_display="User",
            content="Edited content",
            message_id="msg1",
            is_edit=True,
        )
        harness.bus.publish("discord", evt)

        # Assert
        assert len(harness.irc.sent_messages) == 1
        await harness.stop()

    @pytest.mark.asyncio
    async def test_action_message_flag(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()
        from bridge.events import message_in

        # Act - send action message
        _, evt = message_in(
            origin="irc",
            channel_id="irc.libera.chat/#test",
            author_id="user1",
            author_display="User",
            content="does something",
            message_id="msg1",
            is_action=True,
        )
        harness.bus.publish("irc", evt)

        # Assert
        assert len(harness.discord.sent_messages) == 1
        await harness.stop()


class TestMultipleMessages:
    """Test handling multiple messages."""

    @pytest.mark.asyncio
    async def test_multiple_messages_in_order(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()

        # Act
        for i in range(5):
            harness.simulate_discord_message(
                channel_id="123",
                author_id=f"user{i}",
                author_display=f"User{i}",
                content=f"Message {i}",
                message_id=f"msg{i}",
            )

        # Assert
        assert len(harness.irc.sent_messages) == 5
        for i, msg in enumerate(harness.irc.sent_messages):
            assert msg.content == f"Message {i}"
            assert msg.author_display == f"User{i}"
        await harness.stop()

    @pytest.mark.asyncio
    async def test_messages_from_different_users(self, harness: BridgeTestHarness):
        # Arrange
        await harness.start()
        users = ["Alice", "Bob", "Charlie"]

        # Act
        for user in users:
            harness.simulate_discord_message(
                channel_id="123",
                author_id=user.lower(),
                author_display=user,
                content=f"Hello from {user}",
            )

        # Assert
        assert len(harness.irc.sent_messages) == 3
        for i, user in enumerate(users):
            assert harness.irc.sent_messages[i].author_display == user
        await harness.stop()
