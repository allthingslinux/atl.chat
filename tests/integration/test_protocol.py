"""IRC Protocol Compliance Tests

Comprehensive tests for IRC protocol compliance using the controller framework.
Tests cover RFC1459, RFC2812, and modern IRC specifications.
"""

import time

import pytest

from ..utils.base_test_cases import BaseServerTestCase
from ..utils.specifications import mark_specifications


@pytest.fixture(scope="function")
def controller(unrealircd_container, prepared_config_dir):
    """Controller fixture with Docker container."""
    from ..controllers.base_controllers import TestCaseControllerConfig
    from ..controllers.unrealircd_controller import get_unrealircd_controller_class

    controller_class = get_unrealircd_controller_class()
    config = TestCaseControllerConfig()
    controller = controller_class(config, container_fixture=unrealircd_container)

    # Set the controller's directory to the prepared config dir
    controller.directory = prepared_config_dir

    print(f"DEBUG: Controller created: {controller}")
    print(f"DEBUG: Controller container: {getattr(controller, 'container', 'no container attr')}")
    print(f"DEBUG: Container fixture: {unrealircd_container}")
    print(f"DEBUG: Config dir: {prepared_config_dir}")
    print(f"DEBUG: Files in config dir: {list(prepared_config_dir.glob('*'))}")

    return controller


class TestConnectionProtocol(BaseServerTestCase):
    """Test basic IRC connection and registration protocols."""

    def setup_method(self, method):
        """Override setup to use controller fixture."""
        # Controller will be injected via autouse fixture
        if hasattr(self, "controller") and self.controller is not None:
            # Set default test parameters
            self.password = None
            self.ssl = True  # Port 6697 is TLS-only
            self.run_services = False
            self.faketime = None
            self.server_support = None

            # Run the controller (hostname/port already set by inject_controller fixture)
            self.controller.run(
                self.hostname,
                self.port,
                password=self.password,
                ssl=self.ssl,
                run_services=self.run_services,
                faketime=self.faketime,
            )

        self.clients = {}

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_basic_connection_registration(self):
        """Test basic client connection and registration."""
        # Set up test state (don't call controller.run() since container is already started)
        client_name = self.addClient("testuser")
        self.sendLine(client_name, "NICK testuser")
        self.sendLine(client_name, "USER username * * :Realname")
        messages = self.skipToWelcome(client_name)
        welcome = messages[-1]  # The last message should be 001
        self.assertMessageMatch(welcome, command="001")

        # Test PING/PONG
        self.sendLine(client_name, "PING test123")
        pong = self.getMessage(client_name)
        self.assertMessageMatch(pong, command="PONG", params=["irc.atl.dev", "test123"])

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_nick_registration_collision(self):
        """Test nickname registration and collision handling."""
        # Register first client
        client1 = self.connectClient("alice")

        # Register second client with same nick (should get error)
        client2 = self.addClient("client2")
        self.sendLine(client2, "NICK alice")  # Same nick as client1
        self.sendLine(client2, "USER bob 0 * :Bob User")

        # Should receive nick in use error
        error_msg = self.getRegistrationMessage(client2)
        self.assertIn(error_msg.command, ["433", "432"])

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_nick_change(self):
        """Test nickname changes."""
        client = self.connectClient("alice")
        original_nick = "alice"
        new_nick = f"bob_{int(time.time())}"

        # Change nickname
        self.sendLine(client, f"NICK {new_nick}")

        # Should receive NICK message
        nick_msg = self.getMessage(client)
        self.assertMessageMatch(nick_msg, command="NICK", params=[new_nick], nick=original_nick)

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_server_info_commands(self):
        """Test server information commands."""
        client = self.connectClient("testuser")

        # Test VERSION command
        self.sendLine(client, "VERSION")
        version_msg = self.getMessage(client)
        self.assertMessageMatch(version_msg, command="351")

        # Test TIME command
        self.sendLine(client, "TIME")
        time_msg = self.getMessage(client)
        self.assertMessageMatch(time_msg, command="391")

        # Test INFO command
        self.sendLine(client, "INFO")
        info_msg = self.getMessage(client)
        self.assertIn(info_msg.command, ["371", "374"])


class TestChannelProtocol(BaseServerTestCase):
    """Test IRC channel operations and protocols."""

    def setup_method(self, method):
        """Override setup to use controller fixture."""
        # Controller will be injected via autouse fixture
        if hasattr(self, "controller") and self.controller is not None:
            # Set default test parameters
            self.password = None
            self.ssl = True  # Port 6697 is TLS-only
            self.run_services = False
            self.faketime = None
            self.server_support = None

            # Run the controller (hostname/port already set by inject_controller fixture)
            self.controller.run(
                self.hostname,
                self.port,
                password=self.password,
                ssl=self.ssl,
                run_services=self.run_services,
                faketime=self.faketime,
            )

        self.clients = {}

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_channel_join_part(self):
        """Test joining and parting channels."""
        client = self.connectClient("alice")
        test_channel = f"#test_{int(time.time())}"

        # Join channel
        self.joinChannel(client, test_channel)

        # Should receive JOIN confirmation and channel info
        messages = self.getMessages(client)
        join_found = any(msg.command == "JOIN" and msg.params[0] == test_channel for msg in messages)
        names_found = any(msg.command == "353" for msg in messages)
        end_names_found = any(msg.command == "366" for msg in messages)

        self.assertTrue(join_found, f"Should receive JOIN for {test_channel}")
        self.assertTrue(names_found, "Should receive RPL_NAMREPLY")
        self.assertTrue(end_names_found, "Should receive RPL_ENDOFNAMES")

        # Part channel
        self.sendLine(client, f"PART {test_channel} :Leaving")
        part_msg = self.getMessage(client)
        self.assertMessageMatch(part_msg, command="PART", params=[test_channel])

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_multiple_channel_join(self):
        """Test joining multiple channels simultaneously."""
        client = self.connectClient("alice")

        channel1 = f"#multi1_{int(time.time())}"
        channel2 = f"#multi2_{int(time.time())}"

        # Join multiple channels
        self.sendLine(client, f"JOIN {channel1},{channel2}")

        # Should receive JOIN messages for both channels
        messages = self.getMessages(client)
        joined_channels = {msg.params[0] for msg in messages if msg.command == "JOIN"}

        self.assertIn(channel1, joined_channels)
        self.assertIn(channel2, joined_channels)


class TestMessagingProtocol(BaseServerTestCase):
    """Test IRC messaging protocols (PRIVMSG, NOTICE)."""

    def setup_method(self, method):
        """Override setup to use controller fixture."""
        # Controller will be injected via autouse fixture
        if hasattr(self, "controller") and self.controller is not None:
            # Set default test parameters
            self.password = None
            self.ssl = True  # Port 6697 is TLS-only
            self.run_services = False
            self.faketime = None
            self.server_support = None

            # Run the controller (hostname/port already set by inject_controller fixture)
            self.controller.run(
                self.hostname,
                self.port,
                password=self.password,
                ssl=self.ssl,
                run_services=self.run_services,
                faketime=self.faketime,
            )

        self.clients = {}

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_privmsg_to_channel(self):
        """Test PRIVMSG to channels."""
        client1 = self.connectClient("alice")
        client2 = self.connectClient("bob")

        test_channel = f"#msgtest_{int(time.time())}"

        self.joinChannel(client1, test_channel)
        self.getMessages(client1)
        self.joinChannel(client2, test_channel)
        self.getMessages(client2)

        # Send message from client1
        test_message = f"Hello from Alice {int(time.time())}"
        self.sendLine(client1, f"PRIVMSG {test_channel} :{test_message}")
        self.getMessages(client1)

        # Client2 should receive the message
        messages = self.getMessages(client2)
        privmsg_found = any(
            msg.command == "PRIVMSG" and msg.params[0] == test_channel and test_message in msg.params[1]
            for msg in messages
        )
        self.assertTrue(privmsg_found, "Client2 should receive PRIVMSG from client1")

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_privmsg_to_user(self):
        """Test PRIVMSG to individual users."""
        client1 = self.connectClient("alice")
        client2 = self.connectClient("bob")

        # Send private message
        private_msg = f"Private message {int(time.time())}"
        self.sendLine(client1, f"PRIVMSG bob :{private_msg}")

        # Client2 should receive the private message
        privmsg = self.getMessage(client2)
        self.assertMessageMatch(privmsg, command="PRIVMSG", params=["bob", private_msg])

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_privmsg_errors(self):
        """Test PRIVMSG error conditions."""
        client = self.connectClient("alice")

        # Try to message non-existent user
        self.sendLine(client, "PRIVMSG nonexistent :Hello?")
        error_msg = self.getMessage(client)
        self.assertMessageMatch(error_msg, command="401")

        # Try to message non-existent channel
        self.sendLine(client, "PRIVMSG #nonexistent :Hello?")
        error_msg = self.getMessage(client)
        self.assertIn(error_msg.command, ["401", "403", "404"])

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_notice_vs_privmsg(self):
        """Test NOTICE vs PRIVMSG behavior."""
        client1 = self.connectClient("alice")
        client2 = self.connectClient("bob")

        test_channel = f"#noticetest_{int(time.time())}"

        self.joinChannel(client1, test_channel)
        self.joinChannel(client2, test_channel)
        self.getMessages(client2)

        # Send NOTICE
        notice_text = f"Notice {int(time.time())}"
        self.sendLine(client1, f"NOTICE {test_channel} :{notice_text}")
        self.getMessages(client1)

        # Client2 should receive NOTICE
        notice = self.getMessage(client2)
        self.assertMessageMatch(notice, command="NOTICE", params=[test_channel, notice_text])


class TestMultipleClients(BaseServerTestCase):
    """Test scenarios with multiple clients."""

    def setup_method(self, method):
        """Override setup to use controller fixture."""
        # Controller will be injected via autouse fixture
        if hasattr(self, "controller") and self.controller is not None:
            # Set default test parameters
            self.password = None
            self.ssl = True  # Port 6697 is TLS-only
            self.run_services = False
            self.faketime = None
            self.server_support = None

            # Run the controller (hostname/port already set by inject_controller fixture)
            self.controller.run(
                self.hostname,
                self.port,
                password=self.password,
                ssl=self.ssl,
                run_services=self.run_services,
                faketime=self.faketime,
            )

        self.clients = {}

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_multiple_clients_channel_chat(self):
        """Test multiple clients chatting in a channel."""
        clients = []
        nicks = []

        for i in range(3):
            nick = f"multiuser{i}_{int(time.time())}"
            client = self.connectClient(nick)
            clients.append(client)
            nicks.append(nick)

        test_channel = f"#multitest_{int(time.time())}"

        # Join all clients to channel
        for client in clients:
            self.joinChannel(client, test_channel)

        # Sync all clients
        for client in clients:
            self.getMessages(client)

        # Have client 0 send a message
        broadcast_msg = f"Broadcast from {nicks[0]} at {int(time.time())}"
        self.sendLine(clients[0], f"PRIVMSG {test_channel} :{broadcast_msg}")

        # All other clients should receive it
        for i, client in enumerate(clients[1:], 1):
            messages = self.getMessages(client)
            received = any(
                msg.command == "PRIVMSG" and msg.params[0] == test_channel and broadcast_msg in msg.params[1]
                for msg in messages
            )
            self.assertTrue(received, f"Client {i} should receive broadcast message")

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_client_reconnection(self):
        """Test client disconnection and reconnection."""
        client = self.connectClient("reconnect_test")

        # Verify initial connection
        ping_msg = self.getMessage(client)
        self.assertIn(ping_msg.command, ["PING", "001"])

        # Disconnect client
        self.removeClient(client)

        # Reconnect with same nick (may get nick in use)
        new_client = self.connectClient("reconnect_test")

        # Should either succeed or get nick collision error
        response = self.getRegistrationMessage(new_client)
        self.assertIn(response.command, ["001", "433"])


class TestEdgeCases(BaseServerTestCase):
    """Test IRC protocol edge cases and error conditions."""

    def setup_method(self, method):
        """Override setup to use controller fixture."""
        # Controller will be injected via autouse fixture
        if hasattr(self, "controller") and self.controller is not None:
            # Set default test parameters
            self.password = None
            self.ssl = True  # Port 6697 is TLS-only
            self.run_services = False
            self.faketime = None
            self.server_support = None

            # Run the controller (hostname/port already set by inject_controller fixture)
            self.controller.run(
                self.hostname,
                self.port,
                password=self.password,
                ssl=self.ssl,
                run_services=self.run_services,
                faketime=self.faketime,
            )

        self.clients = {}

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    def test_invalid_nickname(self):
        """Test handling of invalid nicknames."""
        client = self.addClient("client1")

        # Try nickname that's too long
        long_nick = "a" * 50
        self.sendLine(client, f"NICK {long_nick}")
        self.sendLine(client, "USER test 0 * :Test User")

        # Should either succeed (if server allows) or get error
        response = self.getRegistrationMessage(client)
        self.assertIn(response.command, ["001", "432"])

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    def test_command_case_insensitivity(self):
        """Test that commands are case insensitive."""
        client = self.addClient("client1")

        # Send commands in mixed case
        test_nick = f"mixedcase_{int(time.time())}"
        self.sendLine(client, f"nick {test_nick}")
        self.sendLine(client, "user MixedCase 0 * :Mixed Case User")

        # Should still work
        welcome = self.getRegistrationMessage(client)
        self.assertMessageMatch(welcome, command="001")

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_empty_messages(self):
        """Test handling of empty messages."""
        client = self.connectClient("alice")

        # Try to send empty PRIVMSG to channel
        test_channel = f"#empty_{int(time.time())}"
        self.joinChannel(client, test_channel)

        self.sendLine(client, f"PRIVMSG {test_channel} :")

        # Should receive error or no response
        response = self.getMessage(client)
        # Server may respond with various codes or nothing
        self.assertIsNotNone(response)

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_connection_limits(self):
        """Test connection limits if any."""
        clients = []

        try:
            # Try to create multiple connections
            for i in range(5):
                nick = f"limit_test_{i}_{int(time.time())}"
                client = self.connectClient(nick)
                clients.append(client)

            # Should have successful connections
            self.assertGreater(len(clients), 0)

        finally:
            # Cleanup
            for client in clients:
                self.removeClient(client)
