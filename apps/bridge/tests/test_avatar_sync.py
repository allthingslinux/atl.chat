"""Tests for avatar syncing functionality."""

from __future__ import annotations


class TestAvatarSync:
    """Test avatar URL handling and caching."""

    def test_avatar_url_in_message_in(self):
        # Arrange
        from bridge.events import MessageIn

        # Act
        msg = MessageIn(
            origin="discord",
            channel_id="123456789",
            author_id="987654321",
            author_display="User",
            content="Hello",
            message_id="msg123",
            avatar_url="https://cdn.discord.com/avatars/987654321/abc123.png",
        )

        # Assert
        assert msg.avatar_url == "https://cdn.discord.com/avatars/987654321/abc123.png"

    def test_message_without_avatar_url(self):
        # Arrange
        from bridge.events import MessageIn

        # Act
        msg = MessageIn(
            origin="irc",
            channel_id="#test",
            author_id="user!user@host",
            author_display="user",
            content="Hello",
            message_id="msg123",
        )

        # Assert
        assert msg.avatar_url is None

    def test_avatar_url_formats(self):
        # Arrange
        from bridge.events import MessageIn

        avatar_urls = [
            "https://cdn.discord.com/avatars/123/abc.png",
            "https://cdn.discord.com/avatars/123/abc.gif",
            "https://cdn.discord.com/avatars/123/abc.webp",
        ]

        # Act & Assert
        for url in avatar_urls:
            msg = MessageIn(
                origin="discord",
                channel_id="123456789",
                author_id="987654321",
                author_display="User",
                content="Test",
                message_id="msg123",
                avatar_url=url,
            )
            assert msg.avatar_url == url
            assert msg.avatar_url is not None
            assert msg.avatar_url.startswith("https://cdn.discord.com")


class TestAvatarHashing:
    """Test avatar URL is preserved through the message pipeline."""

    def test_avatar_url_preserved_in_message_out(self):
        from bridge.events import MessageOut

        msg = MessageOut(
            target_origin="discord",
            channel_id="123",
            author_id="u1",
            author_display="User",
            content="hi",
            message_id="m1",
            avatar_url="https://cdn.discord.com/avatars/123/abc.png",
        )
        assert msg.avatar_url == "https://cdn.discord.com/avatars/123/abc.png"

    def test_different_users_have_different_avatar_urls(self):
        from bridge.events import MessageIn

        msg1 = MessageIn(
            "discord",
            "123",
            "u1",
            "A",
            "hi",
            "m1",
            avatar_url="https://cdn.discord.com/avatars/1/a.png",
        )
        msg2 = MessageIn(
            "discord",
            "123",
            "u2",
            "B",
            "hi",
            "m2",
            avatar_url="https://cdn.discord.com/avatars/2/b.png",
        )
        assert msg1.avatar_url != msg2.avatar_url
