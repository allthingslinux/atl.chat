"""Tests for action messages and message formatting."""

from __future__ import annotations

from bridge.events import MessageIn


class TestActionMessages:
    """Test /me action message handling."""

    def test_action_message_flag_set(self):
        # Act
        msg = MessageIn(
            origin="irc",
            channel_id="#test",
            author_id="user!user@host",
            author_display="user",
            content="waves hello",
            message_id="msg123",
            is_action=True,
        )

        # Assert
        assert msg.is_action is True
        assert msg.content == "waves hello"

    def test_regular_message_not_action(self):
        # Act
        msg = MessageIn(
            origin="discord",
            channel_id="123456789",
            author_id="987654321",
            author_display="User",
            content="Hello everyone",
            message_id="msg123",
        )

        # Assert
        assert msg.is_action is False

    def test_action_message_from_different_origins(self):
        # Arrange
        origins = ["discord", "irc", "xmpp"]

        # Act & Assert
        for origin in origins:
            msg = MessageIn(
                origin=origin,
                channel_id="test-channel",
                author_id="test-user",
                author_display="TestUser",
                content="does something",
                message_id=f"msg-{origin}",
                is_action=True,
            )
            assert msg.is_action is True
            assert msg.origin == origin


class TestMessageFormatting:
    """Test message content formatting."""

    def test_message_with_unicode_emoji(self):
        # Act
        msg = MessageIn(
            origin="discord",
            channel_id="123456789",
            author_id="987654321",
            author_display="User",
            content="Hello 👋 World 🌍",
            message_id="msg123",
        )

        # Assert
        assert "👋" in msg.content
        assert "🌍" in msg.content

    def test_message_with_newlines(self):
        # Act
        msg = MessageIn(
            origin="discord",
            channel_id="123456789",
            author_id="987654321",
            author_display="User",
            content="Line 1\nLine 2\nLine 3",
            message_id="msg123",
        )

        # Assert
        assert "\n" in msg.content
        assert msg.content.count("\n") == 2

    def test_message_with_markdown(self):
        # Act
        msg = MessageIn(
            origin="discord",
            channel_id="123456789",
            author_id="987654321",
            author_display="User",
            content="**bold** *italic* `code`",
            message_id="msg123",
        )

        # Assert
        assert "**bold**" in msg.content
        assert "*italic*" in msg.content
        assert "`code`" in msg.content

    def test_message_with_urls(self):
        # Act
        msg = MessageIn(
            origin="irc",
            channel_id="#test",
            author_id="user!user@host",
            author_display="user",
            content="Check out https://example.com and http://test.org",
            message_id="msg123",
        )

        # Assert
        assert "https://example.com" in msg.content
        assert "http://test.org" in msg.content

    def test_empty_message_content(self):
        # Act
        msg = MessageIn(
            origin="xmpp",
            channel_id="room@conference.example.com",
            author_id="user@example.com",
            author_display="User",
            content="",
            message_id="msg123",
        )

        # Assert
        assert msg.content == ""
        assert len(msg.content) == 0

    def test_very_long_message_content(self):
        # Arrange
        long_content = "A" * 5000

        # Act
        msg = MessageIn(
            origin="discord",
            channel_id="123456789",
            author_id="987654321",
            author_display="User",
            content=long_content,
            message_id="msg123",
        )

        # Assert
        assert len(msg.content) == 5000
        assert msg.content == long_content
