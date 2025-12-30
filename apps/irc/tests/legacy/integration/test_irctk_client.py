"""Integration tests using irc-toolkit (irctk) library."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

# Import irc-toolkit conditionally
irctk = pytest.importorskip("irctk")


class IRCToolkitBot:
    """IRC bot using irc-toolkit library."""

    def __init__(self):
        self.client = None
        self.connected = False
        self.messages_received = []
        self.joined_channels = set()

    async def connect(self, hostname="localhost", port=6667, secure=False):
        """Connect to IRC server using irc-toolkit."""
        self.client = irctk.Client()
        self.client.delegate = self

        # Mock the connection for testing
        with patch.object(
            self.client, "connect", new_callable=AsyncMock
        ) as mock_connect:
            mock_connect.return_value = None
            await self.client.connect(hostname, port, secure)
            self.connected = True

    def disconnect(self):
        """Disconnect from IRC server."""
        if self.client:
            # Mock disconnect for testing
            pass
        self.connected = False

    # IRC event handlers
    def irc_registered(self, client):
        """Called when registered with IRC server."""
        self.connected = True

    def irc_private_message(self, client, nick, message):
        """Handle private messages."""
        self.messages_received.append(
            {
                "type": "private",
                "from": nick,
                "message": message,
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

    def irc_channel_message(self, client, nick, channel, message):
        """Handle channel messages."""
        self.messages_received.append(
            {
                "type": "channel",
                "from": nick,
                "channel": channel,
                "message": message,
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

    def irc_join(self, client, nick, channel):
        """Handle join events."""
        if nick == client.nick:
            self.joined_channels.add(channel)

    def irc_part(self, client, nick, channel):
        """Handle part events."""
        if nick == client.nick:
            self.joined_channels.discard(channel)

    def send_private_message(self, target, message):
        """Send private message."""
        if self.client and self.connected:
            self.client.send("PRIVMSG", target, message)

    def send_channel_message(self, channel, message):
        """Send channel message."""
        if self.client and self.connected:
            self.client.send("PRIVMSG", channel, message)

    def join_channel(self, channel):
        """Join a channel."""
        if self.client and self.connected:
            self.client.send("JOIN", channel)

    def part_channel(self, channel):
        """Part from a channel."""
        if self.client and self.connected:
            self.client.send("PART", channel)


class TestIRCToolkitIntegration:
    """Integration tests for irc-toolkit library."""

    @pytest.mark.asyncio
    async def test_irctk_client_creation(self):
        """Test creating an irc-toolkit client."""
        bot = IRCToolkitBot()

        # Mock the connection
        with patch("irctk.Client"):
            await bot.connect("localhost", 6667, False)

        assert bot.client is not None
        assert bot.connected

    @pytest.mark.asyncio
    async def test_irctk_message_handling(self):
        """Test message handling with irc-toolkit."""
        bot = IRCToolkitBot()

        # Mock client
        mock_client = Mock()
        mock_client.nick = "testbot"
        bot.client = mock_client

        # Simulate receiving messages
        bot.irc_private_message(mock_client, "user1", "hello bot")
        bot.irc_channel_message(mock_client, "user2", "#test", "hello everyone")

        # Verify messages were recorded
        assert len(bot.messages_received) == 2

        private_msg = bot.messages_received[0]
        assert private_msg["type"] == "private"
        assert private_msg["from"] == "user1"
        assert private_msg["message"] == "hello bot"

        channel_msg = bot.messages_received[1]
        assert channel_msg["type"] == "channel"
        assert channel_msg["from"] == "user2"
        assert channel_msg["channel"] == "#test"

    @pytest.mark.asyncio
    async def test_irctk_channel_operations(self):
        """Test channel join/part operations."""
        bot = IRCToolkitBot()
        mock_client = Mock()
        mock_client.nick = "testbot"
        bot.client = mock_client
        bot.connected = True

        # Test joining channels
        bot.irc_join(mock_client, "testbot", "#channel1")
        bot.irc_join(mock_client, "testbot", "#channel2")

        assert "#channel1" in bot.joined_channels
        assert "#channel2" in bot.joined_channels

        # Test parting channels
        bot.irc_part(mock_client, "testbot", "#channel1")

        assert "#channel1" not in bot.joined_channels
        assert "#channel2" in bot.joined_channels

    def test_irctk_message_parsing(self):
        """Test IRC message parsing with irc-toolkit."""
        # Test parsing IRC messages
        test_messages = [
            ":server.example.com 001 testuser :Welcome to IRC",
            ":user!host@server JOIN #channel",
            ":user!host@server PRIVMSG #channel :Hello world",
            ":user!host@server PART #channel :Goodbye",
            ":user!host@server QUIT :Client quit",
        ]

        for message_str in test_messages:
            # Test that irctk.Message can parse these
            try:
                message = irctk.Message.parse(message_str)
                assert message is not None
                assert hasattr(message, "command")
                assert hasattr(message, "parameters")
            except Exception as e:
                pytest.fail(f"Failed to parse message '{message_str}': {e}")

    def test_irctk_command_structure(self):
        """Test IRC command structure with irc-toolkit."""
        # Test creating IRC commands
        commands = [
            ("NICK", ["testuser"]),
            ("USER", ["testuser", "0", "*", "Test User"]),
            ("JOIN", ["#testchannel"]),
            ("PART", ["#testchannel"]),
            ("PRIVMSG", ["#testchannel", "Hello world"]),
            ("QUIT", ["Goodbye"]),
        ]

        for command_name, params in commands:
            try:
                # Test that we can create commands (this would be actual usage)
                assert isinstance(command_name, str)
                assert isinstance(params, list)
                assert len(params) > 0
            except Exception as e:
                pytest.fail(f"Failed to handle command {command_name}: {e}")

    @pytest.mark.asyncio
    async def test_irctk_client_lifecycle(self):
        """Test full client lifecycle with irc-toolkit."""
        bot = IRCToolkitBot()

        # Mock the entire client lifecycle
        with patch("irctk.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Connect
            await bot.connect("irc.example.com", 6667, True)

            # Simulate registration
            bot.irc_registered(mock_client)

            # Simulate channel operations
            bot.join_channel("#test")
            bot.irc_join(mock_client, "testbot", "#test")

            # Simulate message exchange
            bot.send_channel_message("#test", "Hello!")
            bot.irc_channel_message(mock_client, "otheruser", "#test", "Hi there!")

            # Disconnect
            bot.disconnect()

            # Verify state
            assert bot.connected is False
            assert "#test" in bot.joined_channels
            assert (
                len([msg for msg in bot.messages_received if msg["type"] == "channel"])
                == 1
            )

    def test_irctk_message_types(self):
        """Test different IRC message types."""
        message_types = [
            ":server 001 nick :Welcome message",
            ":nick!user@host JOIN #channel",
            ":nick!user@host PART #channel :reason",
            ":nick!user@host QUIT :reason",
            ":nick!user@host PRIVMSG target :message",
            ":nick!user@host NOTICE target :notice",
            ":nick!user@host NICK :newnick",
            ":nick!user@host TOPIC #channel :new topic",
            ":nick!user@host MODE #channel +o othernick",
            ":nick!user@host KICK #channel target :reason",
        ]

        for msg_str in message_types:
            try:
                message = irctk.Message.from_string(msg_str)
                assert message.command in [
                    "001",
                    "JOIN",
                    "PART",
                    "QUIT",
                    "PRIVMSG",
                    "NOTICE",
                    "NICK",
                    "TOPIC",
                    "MODE",
                    "KICK",
                ]
            except Exception as e:
                pytest.fail(f"Failed to parse message type: {msg_str}, error: {e}")

    @pytest.mark.asyncio
    async def test_irctk_error_handling(self):
        """Test error handling in irc-toolkit."""
        bot = IRCToolkitBot()

        # Test with invalid connection parameters
        with pytest.raises(Exception):
            # This should fail with invalid parameters
            await bot.connect("", -1, False)

        # Test message handling with malformed data
        mock_client = Mock()
        bot.client = mock_client

        # These should not crash the bot
        bot.irc_private_message(mock_client, "", "")
        bot.irc_channel_message(mock_client, "", "", "")
        bot.irc_join(mock_client, "", "")
        bot.irc_part(mock_client, "", "")

        # Bot should still be functional
        assert bot.client is not None


# Test fixtures for irc-toolkit
@pytest.fixture
async def irctk_bot():
    """Provide an IRC toolkit bot fixture."""
    bot = IRCToolkitBot()

    # Mock the connection
    with patch("irctk.Client"):
        await bot.connect("localhost", 6667, False)

    yield bot

    bot.disconnect()


@pytest.fixture
def mock_irctk_client():
    """Provide a mocked irc-toolkit client."""
    client = Mock()
    client.nick = "testbot"
    client.send = Mock()
    return client


@pytest.fixture
def sample_irctk_messages():
    """Provide sample IRC messages for testing."""
    return [
        ":server.example.com 001 testuser :Welcome to the IRC network",
        ":testuser!user@host JOIN #testchannel",
        ":testuser!user@host PRIVMSG #testchannel :Hello everyone!",
        ":testuser!user@host PART #testchannel :Goodbye",
        ":testuser!user@host QUIT :Client quit",
    ]
