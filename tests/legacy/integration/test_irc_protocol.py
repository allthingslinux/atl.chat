"""IRC protocol integration tests using the controller framework."""

import time

import pytest

from ..utils.base_test_cases import BaseServerTestCase
from ..utils.specifications import mark_specifications


class TestIRCConnectionProtocol(BaseServerTestCase):
    """Test basic IRC connection and registration protocols."""

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_basic_connection_registration(self):
        """Test basic client connection and registration."""
        # Use the controller's connectClient helper method
        client = self.connectClient("testuser")

        # Should receive welcome message (001)
        welcome = self.getRegistrationMessage(client)
        self.assertMessageMatch(welcome, command="001")

        # Test PING/PONG
        self.sendLine(client, "PING test123")
        pong = self.getMessage(client)
        self.assertMessageMatch(pong, command="PONG", params=["test123"])

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_nick_registration(self):
        """Test nickname registration and collision handling."""
        # Register first client
        self.connectClient("alice")

        # Register second client with same nick (should get error)
        client2 = self.addClient("client2")
        self.sendLine(client2, "NICK alice")  # Same nick as client1
        self.sendLine(client2, "USER bob 0 * :Bob User")

        # Should receive nick in use error
        error_msg = self.getRegistrationMessage(client2)
        self.assertIn(error_msg.command, ["433", "432"])  # ERR_NICKNAMEINUSE or ERR_ERRONEUSNICKNAME

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_nick_change(self):
        """Test nickname changes."""
        client = self.connectClient("alice")

        # Change nickname
        self.sendLine(client, "NICK bob")

        # Should receive NICK message
        nick_msg = self.getMessage(client)
        self.assertMessageMatch(nick_msg, command="NICK", params=["bob"], nick="alice")

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
        self.assertMessageMatch(version_msg, command="351")  # RPL_VERSION

        # Test TIME command
        self.sendLine(client, "TIME")
        time_msg = self.getMessage(client)
        self.assertMessageMatch(time_msg, command="391")  # RPL_TIME

        # Test INFO command
        self.sendLine(client, "INFO")
        info_msg = self.getMessage(client)
        self.assertIn(info_msg.command, ["371", "374"])  # RPL_INFO or RPL_ENDOFINFO


class TestIRCChannelProtocol(BaseServerTestCase):
    """Test IRC channel operations and protocols."""

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
        names_found = any(msg.command == "353" for msg in messages)  # RPL_NAMREPLY
        end_names_found = any(msg.command == "366" for msg in messages)  # RPL_ENDOFNAMES

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

        self.assertIn(channel1, joined_channels, f"Should join {channel1}")
        self.assertIn(channel2, joined_channels, f"Should join {channel2}")

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_channel_join_errors(self):
        """Test channel join error conditions."""
        client = self.connectClient("alice")

        # Try to join non-existent channel (should work - channels are created on join)
        # Try to join channel that requires key without key
        self.sendLine(client, "JOIN #keyed_channel key_required")
        self.getMessage(client)
        # This depends on server configuration - may succeed or fail

        # Test invalid channel name
        self.sendLine(client, "JOIN invalid&channel")
        # Should either succeed or get error
        response = self.getMessage(client)
        self.assertIn(response.command, ["JOIN", "403", "479"])  # JOIN success or various errors


class TestIRCMessagingProtocol(BaseServerTestCase):
    """Test IRC messaging protocols (PRIVMSG, NOTICE)."""

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_privmsg_to_channel(self):
        """Test PRIVMSG to channels."""
        # Set up two clients in a channel
        client1 = self.connectClient("alice")
        client2 = self.connectClient("bob")

        test_channel = f"#msgtest_{int(time.time())}"

        self.joinChannel(client1, test_channel)
        self.getMessages(client1)  # sync

        self.joinChannel(client2, test_channel)
        self.getMessages(client2)  # sync

        # Send message from client1
        test_message = f"Hello from Alice {int(time.time())}"
        self.sendLine(client1, f"PRIVMSG {test_channel} :{test_message}")
        self.getMessages(client1)  # sync

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
        self.assertMessageMatch(error_msg, command="401")  # ERR_NOSUCHNICK

        # Try to message non-existent channel
        self.sendLine(client, "PRIVMSG #nonexistent :Hello?")
        error_msg = self.getMessage(client)
        self.assertIn(error_msg.command, ["401", "403", "404"])  # Various error codes possible

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
        self.getMessages(client2)  # sync

        # Send NOTICE
        notice_text = f"Notice {int(time.time())}"
        self.sendLine(client1, f"NOTICE {test_channel} :{notice_text}")
        self.getMessages(client1)  # sync

        # Client2 should receive NOTICE
        notice = self.getMessage(client2)
        self.assertMessageMatch(notice, command="NOTICE", params=[test_channel, notice_text])


class TestIRCMultipleClients(BaseServerTestCase):
    """Test scenarios with multiple clients."""

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_multiple_clients_channel_chat(self):
        """Test multiple clients chatting in a channel."""
        # Create multiple clients
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
        self.assertIn(response.command, ["001", "433"])  # Welcome or nick in use


class TestIRCEdgeCases(BaseServerTestCase):
    """Test IRC protocol edge cases and error conditions."""

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    def test_invalid_nickname(self):
        """Test handling of invalid nicknames."""
        client = self.addClient("client1")

        # Try nickname that's too long
        long_nick = "a" * 50  # UnrealIRCd has reasonable limits
        self.sendLine(client, f"NICK {long_nick}")
        self.sendLine(client, "USER test 0 * :Test User")

        # Should either succeed (if server allows) or get error
        response = self.getRegistrationMessage(client)
        self.assertIn(response.command, ["001", "432"])  # Welcome or erroneous nickname

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
        self.assertIsNotNone(response, "Should get some response to empty message")

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_connection_limits(self):
        """Test connection limits if any."""
        clients = []

        try:
            # Try to create multiple connections
            for i in range(5):  # Reasonable number for testing
                nick = f"limit_test_{i}_{int(time.time())}"
                client = self.connectClient(nick)
                clients.append(client)

            # Should have successful connections
            self.assertGreater(len(clients), 0, "Should create at least one connection")

        finally:
            # Cleanup
            for client in clients:
                self.removeClient(client)
