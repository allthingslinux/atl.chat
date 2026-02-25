"""Example tests showing bridge message flow."""

import pytest
from bridge.events import MessageOut
from bridge.gateway.router import ChannelMapping, IrcTarget, XmppTarget

from tests.harness import BridgeTestHarness


@pytest.fixture
def harness():
    """Create test harness with sample mappings."""
    mappings = [
        ChannelMapping(
            discord_channel_id="123456789",
            irc=IrcTarget(server="irc.libera.chat", port=6667, tls=False, channel="#test"),
            xmpp=XmppTarget(muc_jid="test@conference.example.com"),
        )
    ]
    return BridgeTestHarness(mappings)


@pytest.mark.asyncio
async def test_discord_to_irc_message(harness: BridgeTestHarness):
    """Test message from Discord reaches IRC."""
    # Arrange
    await harness.start()

    # Act
    harness.simulate_discord_message(
        channel_id="123456789",
        author_id="user123",
        author_display="TestUser",
        content="Hello from Discord!",
    )

    # Assert
    assert len(harness.irc.sent_messages) == 1
    msg = harness.irc.sent_messages[0]
    assert isinstance(msg, MessageOut)
    assert msg.target_origin == "irc"
    assert msg.content == "Hello from Discord!"
    assert msg.author_display == "TestUser"

    await harness.stop()


@pytest.mark.asyncio
async def test_irc_to_discord_message(harness: BridgeTestHarness):
    """Test message from IRC reaches Discord."""
    # Arrange
    await harness.start()

    # Act
    harness.simulate_irc_message(
        server="irc.libera.chat",
        channel="#test",
        author_id="nick!user@host",
        author_display="IRCUser",
        content="Hello from IRC!",
    )

    # Assert
    assert len(harness.discord.sent_messages) == 1
    msg = harness.discord.sent_messages[0]
    assert isinstance(msg, MessageOut)
    assert msg.target_origin == "discord"
    assert msg.content == "Hello from IRC!"
    assert msg.author_display == "IRCUser"

    await harness.stop()


@pytest.mark.asyncio
async def test_message_not_bridged_to_origin(harness: BridgeTestHarness):
    """Test message doesn't echo back to origin."""
    # Arrange
    await harness.start()

    # Act
    harness.simulate_discord_message(
        channel_id="123456789",
        author_id="user123",
        author_display="TestUser",
        content="Test message",
    )

    # Assert
    assert len(harness.discord.sent_messages) == 0
    assert len(harness.irc.sent_messages) >= 1
    assert len(harness.xmpp.sent_messages) >= 1

    await harness.stop()
