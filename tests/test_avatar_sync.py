"""Tests for avatar syncing functionality."""

from __future__ import annotations

import pytest


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
            assert msg.avatar_url.startswith("https://cdn.discord.com")


class TestAvatarHashing:
    """Test avatar hash generation for caching."""

    def test_avatar_hash_consistency(self):
        # Arrange
        import hashlib

        avatar_url = "https://cdn.discord.com/avatars/123/abc.png"

        # Act
        hash1 = hashlib.md5(avatar_url.encode()).hexdigest()
        hash2 = hashlib.md5(avatar_url.encode()).hexdigest()

        # Assert
        assert hash1 == hash2

    def test_different_urls_different_hashes(self):
        # Arrange
        import hashlib

        url1 = "https://cdn.discord.com/avatars/123/abc.png"
        url2 = "https://cdn.discord.com/avatars/123/def.png"

        # Act
        hash1 = hashlib.md5(url1.encode()).hexdigest()
        hash2 = hashlib.md5(url2.encode()).hexdigest()

        # Assert
        assert hash1 != hash2
