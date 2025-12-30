"""IRC message protocol tests.

Tests for PRIVMSG and NOTICE commands based on irctest patterns.
"""

import pytest

from ..utils.base_test_cases import BaseServerTestCase
from ..utils.specifications import mark_specifications


class PrivmsgTestCase(BaseServerTestCase):
    """Test PRIVMSG command functionality."""

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    def test_privmsg_basic(self):
        """Test basic PRIVMSG functionality."""
        # Connect two clients
        self.connectClient("alice")
        self.connectClient("bob")

        # Join a channel
        self.joinChannel(1, "#test")
        self.getMessages(1)  # synchronize
        self.joinChannel(2, "#test")
        self.getMessages(2)  # synchronize

        # Send a message
        self.sendLine(1, "PRIVMSG #test :Hello from Alice!")
        self.getMessages(1)  # synchronize

        # Check that bob received the message
        messages = [msg for msg in self.getMessages(2) if msg.command == "PRIVMSG"]
        self.assertEqual(len(messages), 1)
        self.assertMessageMatch(messages[0], command="PRIVMSG", params=["#test", "Hello from Alice!"])

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    def test_privmsg_to_user(self):
        """Test PRIVMSG to a specific user."""
        self.connectClient("alice")
        self.connectClient("bob")

        # Send private message
        self.sendLine(1, "PRIVMSG bob :Private message!")
        self.getMessages(1)  # synchronize

        # Check that bob received the message
        messages = [msg for msg in self.getMessages(2) if msg.command == "PRIVMSG"]
        self.assertEqual(len(messages), 1)
        self.assertMessageMatch(messages[0], command="PRIVMSG", params=["bob", "Private message!"])

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    def test_privmsg_nonexistent_channel(self):
        """Test PRIVMSG to nonexistent channel."""
        self.connectClient("alice")
        self.sendLine(1, "PRIVMSG #nonexistent :Hello?")
        msg = self.getMessage(1)

        # Should receive an error
        self.assertIn(msg.command, ["401", "403", "404"])  # ERR_NOSUCHNICK/NOSUCHCHANNEL/CANNOTSENDTOCHAN

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    def test_privmsg_nonexistent_user(self):
        """Test PRIVMSG to nonexistent user."""
        self.connectClient("alice")
        self.sendLine(1, "PRIVMSG nonexistent :Hello?")
        msg = self.getMessage(1)

        # Should receive ERR_NOSUCHNICK
        self.assertMessageMatch(msg, command="401", params=["alice", "nonexistent", self._match_anystr()])

    def _match_anystr(self):
        """Helper to match any string (for error message contents)."""
        import re

        return re.compile(r".*")


class NoticeTestCase(BaseServerTestCase):
    """Test NOTICE command functionality."""

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    def test_notice_basic(self):
        """Test basic NOTICE functionality."""
        # Connect two clients
        self.connectClient("alice")
        self.connectClient("bob")

        # Join a channel
        self.joinChannel(1, "#test")
        self.getMessages(1)  # synchronize
        self.joinChannel(2, "#test")
        self.getMessages(2)  # synchronize

        # Send a notice
        self.sendLine(1, "NOTICE #test :Notice from Alice!")
        self.getMessages(1)  # synchronize

        # Check that bob received the notice
        notices = [msg for msg in self.getMessages(2) if msg.command == "NOTICE"]
        self.assertEqual(len(notices), 1)
        self.assertMessageMatch(notices[0], command="NOTICE", params=["#test", "Notice from Alice!"])


class PingPongTestCase(BaseServerTestCase):
    """Test PING/PONG functionality."""

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    def test_ping_pong(self):
        """Test PING/PONG mechanism."""
        self.connectClient("alice")

        # Send PING
        ping_token = "test123"
        self.sendLine(1, f"PING {ping_token}")

        # Should receive PONG
        pong = self.getMessage(1)
        self.assertMessageMatch(pong, command="PONG", params=[ping_token])


class NickTestCase(BaseServerTestCase):
    """Test NICK command functionality."""

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    def test_nick_change(self):
        """Test changing nickname."""
        self.connectClient("alice")

        # Change nick
        self.sendLine(1, "NICK bob")

        # Should receive NICK message
        nick_msg = self.getMessage(1)
        self.assertMessageMatch(nick_msg, command="NICK", params=["bob"], nick="alice")

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    def test_nick_in_use(self):
        """Test nickname collision."""
        self.connectClient("alice")
        self.connectClient("alice")  # Try to use same nick

        # Second client should get error
        error_msg = self.getMessage(2)
        self.assertIn(error_msg.command, ["433", "432"])  # ERR_NICKNAMEINUSE or ERR_ERRONEUSNICKNAME


class JoinTestCase(BaseServerTestCase):
    """Test JOIN command functionality."""

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    def test_join_channel(self):
        """Test joining a channel."""
        self.connectClient("alice")

        # Join channel
        self.joinChannel(1, "#test")

        # Should receive JOIN and RPL_ENDOFNAMES
        messages = self.getMessages(1)
        join_found = any(msg.command == "JOIN" and msg.params[0] == "#test" for msg in messages)
        endofnames_found = any(msg.command == "366" for msg in messages)

        self.assertTrue(join_found, "Should receive JOIN message")
        self.assertTrue(endofnames_found, "Should receive RPL_ENDOFNAMES (366)")

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    def test_join_multiple_channels(self):
        """Test joining multiple channels."""
        self.connectClient("alice")

        # Join multiple channels
        self.sendLine(1, "JOIN #test1,#test2")
        self.getMessages(1)  # synchronize

        # Should receive JOIN messages for both channels
        messages = self.getMessages(1)
        channels_joined = {msg.params[0] for msg in messages if msg.command == "JOIN"}

        self.assertIn("#test1", channels_joined)
        self.assertIn("#test2", channels_joined)
