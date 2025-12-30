"""Test the new controller pattern integration.

This test demonstrates the irctest-inspired controller pattern working
with our existing Docker-based IRC infrastructure.
"""

import pytest
from typing import cast

from ..utils.base_test_cases import BaseServerTestCase
from ..controllers import get_unrealircd_controller_class


class TestControllerPattern(BaseServerTestCase):
    """Test the controller pattern integration."""

    @staticmethod
    def controller_class():
        """Override to use our UnrealIRCd controller."""
        return get_unrealircd_controller_class()

    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_controller_basic_functionality(self):
        """Test that the controller can start and manage an IRC server."""
        # Controller should already be started by setUp
        assert self.controller.proc is not None
        assert self.controller.port_open

        # Test basic client connection
        client = self.addClient("testuser")
        self.sendLine(client, "NICK testuser")
        self.sendLine(client, "USER testuser 0 * :Test User")

        # Should receive welcome
        welcome_msg = self.getRegistrationMessage(client)
        assert welcome_msg.command == "001"

        # Test PING/PONG
        self.sendLine(client, "PING test123")
        pong_msg = self.getMessage(client)
        assert pong_msg.command == "PONG"
        assert pong_msg.params == ["test123"]

    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_controller_channel_operations(self):
        """Test channel operations with the controller."""
        # Connect client
        client = self.addClient("testuser")
        self.sendLine(client, "NICK testuser")
        self.sendLine(client, "USER testuser 0 * :Test User")
        self.skipToWelcome(client)

        # Join channel
        self.joinChannel(client, "#testchannel")

        # Should be able to send messages
        self.sendLine(client, "PRIVMSG #testchannel :Hello from controller test!")

        # Get messages to ensure synchronization
        messages = self.getMessages(client)
        # Should have received the message back (echo or channel message)

    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_controller_multiple_clients(self):
        """Test multiple clients managed by the controller."""
        # Connect two clients
        client1 = self.addClient("user1")
        client2 = self.addClient("user2")

        # Register both
        self.sendLine(client1, "NICK user1")
        self.sendLine(client1, "USER user1 0 * :User One")
        self.skipToWelcome(client1)

        self.sendLine(client2, "NICK user2")
        self.sendLine(client2, "USER user2 0 * :User Two")
        self.skipToWelcome(client2)

        # Have them join a channel and communicate
        self.joinChannel(client1, "#multitest")
        self.getMessages(client1)  # sync

        self.joinChannel(client2, "#multitest")
        self.getMessages(client2)  # sync

        # Send message from client1
        self.sendLine(client1, "PRIVMSG #multitest :Hello from user1!")
        self.getMessages(client1)  # sync

        # Client2 should receive the message
        messages = self.getMessages(client2)
        privmsg_found = any(msg.command == "PRIVMSG" and "#multitest" in msg.params for msg in messages)
        assert privmsg_found, "Client2 should receive PRIVMSG from client1"
