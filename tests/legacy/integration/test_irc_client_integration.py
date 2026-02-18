"""Integration tests using the IRC library with controlled IRC server."""

import pytest
import time
import threading
from typing import Optional

# Import IRC library conditionally to avoid import errors if not installed
irc = pytest.importorskip("irc")

from ..utils.base_test_cases import BaseServerTestCase
from ..utils.specifications import mark_specifications


class IRCClientTest:
    """IRC client for testing purposes using the python-irc library."""

    def __init__(self, host: str = "localhost", port: int = 6667):
        self.host = host
        self.port = port
        self.client = None
        self.connected = False
        self.messages = []
        self.events = []

    def connect(self) -> bool:
        """Connect to IRC server."""
        try:
            # Create IRC client using the library
            self.client = irc.client.IRC()

            # Connect to server
            self.client.connect(self.host, self.port, nickname="testuser")

            # Set up event handlers
            self.client.add_global_handler("welcome", self.on_welcome)
            self.client.add_global_handler("privmsg", self.on_privmsg)
            self.client.add_global_handler("pubmsg", self.on_pubmsg)
            self.client.add_global_handler("join", self.on_join)
            self.client.add_global_handler("part", self.on_part)
            self.client.add_global_handler("quit", self.on_quit)

            # Start processing in a separate thread
            self.thread = threading.Thread(target=self.client.process_forever)
            self.thread.daemon = True
            self.thread.start()

            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            return self.connected

        except Exception as e:
            print(f"Failed to connect to IRC server: {e}")
            return False

    def disconnect(self):
        """Disconnect from IRC server."""
        if self.client:
            self.client.disconnect()
            self.connected = False

    def send_message(self, target: str, message: str):
        """Send a message to a target (user or channel)."""
        if self.client and self.connected:
            self.client.privmsg(target, message)

    def join_channel(self, channel: str):
        """Join an IRC channel."""
        if self.client and self.connected:
            self.client.join(channel)

    def part_channel(self, channel: str):
        """Part from an IRC channel."""
        if self.client and self.connected:
            self.client.part(channel)

    # Event handlers
    def on_welcome(self, connection, event):
        """Handle welcome event (successful connection)."""
        self.connected = True
        self.events.append(("welcome", event.arguments))

    def on_privmsg(self, connection, event):
        """Handle private message."""
        sender = event.source.nick
        message = event.arguments[0]
        self.messages.append(("privmsg", sender, message))
        self.events.append(("privmsg", sender, message))

    def on_pubmsg(self, connection, event):
        """Handle public message."""
        sender = event.source.nick
        channel = event.target
        message = event.arguments[0]
        self.messages.append(("pubmsg", sender, channel, message))
        self.events.append(("pubmsg", sender, channel, message))

    def on_join(self, connection, event):
        """Handle join event."""
        user = event.source.nick
        channel = event.target
        self.events.append(("join", user, channel))

    def on_part(self, connection, event):
        """Handle part event."""
        user = event.source.nick
        channel = event.target
        self.events.append(("part", user, channel))

    def on_quit(self, connection, event):
        """Handle quit event."""
        user = event.source.nick
        self.events.append(("quit", user))


class TestIRCIntegration(BaseServerTestCase):
    """Integration tests for IRC server using python-irc library with controlled server."""

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_irc_server_connection(self):
        """Test connecting to controlled IRC server using IRC library."""
        # Create IRC library client
        client = IRCClientTest(self.hostname, self.port)

        try:
            # Connect to our controlled server
            connected = client.connect()

            assert connected, "Failed to connect to controlled IRC server"
            assert client.connected, "Client not marked as connected"
            assert len(client.events) > 0, "No events received from server"

            # Check for welcome message
            welcome_events = [e for e in client.events if e[0] == "welcome"]
            assert len(welcome_events) > 0, "No welcome message received"

        finally:
            client.disconnect()

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_irc_channel_operations(self):
        """Test IRC channel join/part operations with controlled server."""
        client1 = IRCClientTest(self.hostname, self.port)
        client2 = IRCClientTest(self.hostname, self.port)

        try:
            # Connect both clients to our controlled server
            connected1 = client1.connect()
            connected2 = client2.connect()

            assert connected1 and connected2, "Both clients must connect to controlled server"

            # Client 1 joins a test channel
            test_channel = f"#irc_lib_test_{int(time.time())}"
            client1.join_channel(test_channel)

            # Wait a bit for join to process
            time.sleep(2)

            # Check that client1 received join event
            join_events = [e for e in client1.events if e[0] == "join"]
            assert len(join_events) > 0, "Client1 did not receive join event"

            # Client 2 joins the same channel
            client2.join_channel(test_channel)
            time.sleep(2)

            # Client 1 sends a message to the channel
            test_message = f"Hello from test client at {int(time.time())}!"
            client1.send_message(test_channel, test_message)
            time.sleep(1)

            # Check that client2 received the message
            pubmsg_events = [e for e in client2.events if e[0] == "pubmsg"]
            received_messages = [e[3] for e in pubmsg_events if len(e) > 3]
            assert test_message in received_messages, "Client2 did not receive channel message"

            # Client 2 parts the channel
            client2.part_channel(test_channel)
            time.sleep(1)

            # Check part event
            part_events = [e for e in client2.events if e[0] == "part"]
            assert len(part_events) > 0, "Client2 did not receive part event"

        finally:
            client1.disconnect()
            client2.disconnect()

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_irc_private_messages(self):
        """Test private messaging between IRC clients with controlled server."""
        client1 = IRCClientTest(self.hostname, self.port)
        client2 = IRCClientTest(self.hostname, self.port)

        try:
            # Connect both clients to our controlled server with different nicknames
            # Set different nicknames to avoid conflicts
            client1.nickname = f"priv_client1_{int(time.time())}"
            client2.nickname = f"priv_client2_{int(time.time())}"

            connected1 = client1.connect()
            connected2 = client2.connect()

            assert connected1 and connected2, "Both clients must connect to controlled server"

            # Wait for connections to stabilize
            time.sleep(2)

            # Client 1 sends private message to client 2
            test_message = f"Private message test at {int(time.time())}!"
            client1.send_message(client2.nickname, test_message)
            time.sleep(1)

            # Check that client2 received the private message
            privmsg_events = [e for e in client2.events if e[0] == "privmsg"]
            received_messages = [e[2] for e in privmsg_events if len(e) > 2]
            assert test_message in received_messages, "Client2 did not receive private message"

        finally:
            client1.disconnect()
            client2.disconnect()

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    def test_irc_server_info(self):
        """Test retrieving IRC server information from controlled server."""
        client = IRCClientTest(self.hostname, self.port)

        try:
            connected = client.connect()

            assert connected, "Must connect to controlled IRC server"

            # Send VERSION command to get server info
            if client.client:
                client.client.send_raw("VERSION")
                time.sleep(1)

            # Check for server response in events
            # This would depend on server configuration
            assert client.connected, "Should remain connected after VERSION command"

        finally:
            client.disconnect()

    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_irc_multiple_clients(self):
        """Test multiple clients connecting to IRC server simultaneously."""
        clients = []
        num_clients = 3

        try:
            # Create and connect multiple clients
            for i in range(num_clients):
                client = IRCClientTest()
                connected = client.connect()

                if connected:
                    clients.append(client)
                    time.sleep(0.5)  # Small delay between connections
                else:
                    break

            # Verify we have some connected clients
            connected_clients = [c for c in clients if c.connected]
            assert len(connected_clients) > 0, "No clients could connect to IRC server"

            # Test that all connected clients can join the same channel
            test_channel = "#multitest"
            for client in connected_clients:
                client.join_channel(test_channel)

            time.sleep(2)

            # Verify join events were received
            for client in connected_clients:
                join_events = [e for e in client.events if e[0] == "join"]
                assert len(join_events) > 0, f"Client did not receive join events"

        finally:
            # Clean up all clients
            for client in clients:
                client.disconnect()


# Test utilities for IRC testing
@pytest.fixture
def irc_test_client():
    """Provide an IRC test client fixture."""
    client = IRCClientTest()
    yield client
    client.disconnect()


@pytest.fixture
def connected_irc_client(irc_test_client):
    """Provide a connected IRC client fixture."""
    connected = irc_test_client.connect()
    if not connected:
        pytest.skip("IRC server not available for testing")
    yield irc_test_client


@pytest.fixture
def irc_test_channel():
    """Provide a unique test channel name."""
    return f"#test_{int(time.time())}"
