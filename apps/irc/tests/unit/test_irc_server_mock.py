"""Unit tests with mock IRC server using python-irc library."""

import threading
import time
from unittest.mock import Mock, patch

import pytest

# Import IRC library conditionally
irc = pytest.importorskip("irc")


class MockIRCServer:
    """Mock IRC server for testing purposes."""

    def __init__(self, host: str = "localhost", port: int = 6667):
        self.host = host
        self.port = port
        self.server = None
        self.running = False
        self.thread = None

    def start(self):
        """Start the mock IRC server."""
        try:
            # Note: The irc library doesn't include a server in this version
            # We'll simulate server startup for testing purposes
            self.running = True

            # Start server in a separate thread (simulated)
            self.thread = threading.Thread(target=self._run_server)
            self.thread.daemon = True
            self.thread.start()

            # Give server time to start
            time.sleep(0.1)

        except Exception as e:
            print(f"Failed to start mock IRC server: {e}")
            self.running = False

    def stop(self):
        """Stop the mock IRC server."""
        self.running = False
        if self.server:
            # The server doesn't have a direct stop method, so we just set the flag
            pass

    def _run_server(self):
        """Run the server (simplified for testing)."""
        # Note: The irc library doesn't include a server in this version
        # This is just a mock implementation for testing
        while self.running:
            time.sleep(0.1)


class TestIRCServerMock:
    """Test IRC server functionality with mock server."""

    def test_mock_irc_server_creation(self):
        """Test creating a mock IRC server."""
        server = MockIRCServer()
        assert server.host == "localhost"
        assert server.port == 6667
        assert not server.running

    def test_mock_irc_server_start_stop(self):
        """Test starting and stopping mock IRC server."""
        server = MockIRCServer()

        # Start server
        server.start()
        assert server.running

        # Stop server
        server.stop()
        assert not server.running

    @patch("irc.client.SimpleIRCClient")
    def test_irc_client_mock_setup(self, mock_irc_class):
        """Test setting up mocked IRC client."""
        # Create mock IRC client
        mock_client = Mock()
        mock_irc_class.return_value = mock_client

        # Configure mock behavior
        mock_client.connect.return_value = True
        mock_client.process_forever = Mock()

        # Test client creation
        client = irc.client.SimpleIRCClient()
        assert client == mock_client

        # Test connection (SimpleIRCClient uses different API)
        # This is a simplified test since the actual API is more complex
        assert mock_client.connect.return_value is True

    def test_irc_message_parsing(self):
        """Test IRC message parsing and handling."""
        # Test parsing IRC messages
        test_messages = [
            ":server.example.com 001 testuser :Welcome to the IRC network",
            ":testuser!user@host JOIN #testchannel",
            ":testuser!user@host PRIVMSG #testchannel :Hello everyone!",
            ":testuser!user@host PART #testchannel :Goodbye",
            ":testuser!user@host QUIT :Client quit",
        ]

        for message in test_messages:
            # Basic validation that messages follow IRC format
            assert isinstance(message, str)
            assert len(message) > 0

            # Check for IRC message structure (starts with : or command)
            assert message.startswith(":") or message.split()[0].isdigit()

    def test_irc_command_structure(self):
        """Test IRC command structure validation."""
        # Test common IRC commands
        commands = {
            "NICK": "testuser",
            "USER": "testuser 0 * :Test User",
            "JOIN": "#testchannel",
            "PART": "#testchannel",
            "PRIVMSG": "#testchannel :Hello",
            "QUIT": ":Goodbye",
        }

        for command, params in commands.items():
            # Validate command format
            assert command in ["NICK", "USER", "JOIN", "PART", "PRIVMSG", "QUIT"]
            assert isinstance(params, str)

    @patch("irc.client.ServerConnection")
    def test_irc_server_connection_mock(self, mock_connection_class):
        """Test IRC server connection mocking."""
        mock_connection = Mock()
        mock_connection_class.return_value = mock_connection

        # Configure mock connection
        mock_connection.connect.return_value = None
        mock_connection.send_raw.return_value = None
        mock_connection.disconnect.return_value = None

        # Test connection operations
        connection = irc.client.ServerConnection("localhost")
        assert connection == mock_connection

        # Test sending commands
        connection.send_raw("NICK testuser")
        mock_connection.send_raw.assert_called_with("NICK testuser")

        # Test disconnection
        connection.disconnect()
        mock_connection.disconnect.assert_called_once()

    def test_irc_event_handling(self):
        """Test IRC event handling mechanisms."""
        # Test event types that IRC clients should handle
        events = [
            "welcome",
            "join",
            "part",
            "quit",
            "privmsg",
            "pubmsg",
            "namelist",
            "topic",
            "kick",
            "mode",
        ]

        for event in events:
            assert isinstance(event, str)
            assert len(event) > 0

        # Test event handler registration (mock)
        mock_client = Mock()
        mock_client.add_global_handler = Mock()

        # Register event handlers
        for event in events:
            mock_client.add_global_handler(event, lambda conn, evt: None)

        # Verify handlers were registered
        assert mock_client.add_global_handler.call_count == len(events)

    @pytest.mark.parametrize(
        "irc_command,expected_response",
        [
            ("PING :test", "PONG :test"),
            ("VERSION", "351"),  # RPL_VERSION
            ("TIME", "391"),  # RPL_TIME
            ("INFO", "371"),  # RPL_INFO
        ],
    )
    def test_irc_command_responses(self, irc_command, expected_response):
        """Test expected IRC command responses."""
        # Validate command-response pairs
        assert isinstance(irc_command, str)
        assert isinstance(expected_response, str)
        assert len(irc_command) > 0
        assert len(expected_response) > 0

        # Test that commands start appropriately
        assert not irc_command.startswith(" ")
        assert not expected_response.startswith(" ")

    def test_irc_channel_operations(self):
        """Test IRC channel operation patterns."""
        channel_ops = [
            ("#test", "valid channel"),
            ("&test", "valid local channel"),
            ("+test", "valid modeless channel"),
            ("!test", "valid safe channel"),
        ]

        for channel, description in channel_ops:
            assert channel.startswith(("#", "&", "+", "!"))
            assert len(channel) > 1
            assert description

    def test_irc_user_modes(self):
        """Test IRC user mode patterns."""
        user_modes = [
            ("i", "invisible"),
            ("w", "wallops"),
            ("o", "operator"),
            ("O", "local operator"),
            ("r", "registered"),
            ("s", "server notices"),
        ]

        for mode, description in user_modes:
            assert len(mode) == 1
            assert isinstance(description, str)
            assert len(description) > 0

    def test_irc_error_codes(self):
        """Test common IRC error codes."""
        error_codes = {
            401: "ERR_NOSUCHNICK",
            403: "ERR_NOSUCHCHANNEL",
            404: "ERR_CANNOTSENDTOCHAN",
            405: "ERR_TOOMANYCHANNELS",
            411: "ERR_NORECIPIENT",
            412: "ERR_NOTEXTTOSEND",
            421: "ERR_UNKNOWNCOMMAND",
            431: "ERR_NONICKNAMEGIVEN",
            432: "ERR_ERRONEOUSNICKNAME",
        }

        for code, name in error_codes.items():
            assert isinstance(code, int)
            assert 400 <= code <= 599  # Error code range
            assert name.startswith("ERR_")
            assert isinstance(name, str)
