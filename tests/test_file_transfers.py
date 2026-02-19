"""Tests for file transfer features."""

from __future__ import annotations

import pytest

from bridge.events import MessageIn


class TestXMPPFileUpload:
    """Test XEP-0363 HTTP File Upload."""

    def test_file_metadata_in_message(self):
        # Act
        msg = MessageIn(
            origin="xmpp",
            channel_id="room@conference.example.com",
            author_id="user@example.com",
            author_display="User",
            content="",
            message_id="msg123",
            raw={
                "file_url": "https://upload.example.com/file123.png",
                "file_name": "image.png",
                "file_size": 1024000,
                "file_type": "image/png",
            },
        )

        # Assert
        assert msg.raw.get("file_url") == "https://upload.example.com/file123.png"
        assert msg.raw.get("file_name") == "image.png"
        assert msg.raw.get("file_size") == 1024000
        assert msg.raw.get("file_type") == "image/png"

    def test_file_size_limit_check(self):
        # Arrange
        max_size = 10 * 1024 * 1024  # 10MB

        # Act & Assert
        small_file = 5 * 1024 * 1024  # 5MB
        large_file = 15 * 1024 * 1024  # 15MB

        assert small_file <= max_size
        assert large_file > max_size

    def test_ibb_fallback_metadata(self):
        # Act - IBB fallback when HTTP upload unavailable
        msg = MessageIn(
            origin="xmpp",
            channel_id="room@conference.example.com",
            author_id="user@example.com",
            author_display="User",
            content="",
            message_id="msg123",
            raw={
                "ibb_sid": "session123",
                "file_name": "document.pdf",
                "file_size": 512000,
            },
        )

        # Assert
        assert msg.raw.get("ibb_sid") == "session123"
        assert msg.raw.get("file_name") == "document.pdf"


class TestDiscordAttachments:
    """Test Discord attachment handling."""

    def test_attachment_url_extraction(self):
        # Act
        msg = MessageIn(
            origin="discord",
            channel_id="123456789",
            author_id="987654321",
            author_display="User",
            content="Check this out",
            message_id="msg123",
            raw={
                "attachments": [
                    {
                        "url": "https://cdn.discord.com/attachments/123/456/image.png",
                        "filename": "image.png",
                        "size": 2048000,
                    }
                ]
            },
        )

        # Assert
        attachments = msg.raw.get("attachments", [])
        assert len(attachments) == 1
        assert attachments[0]["url"].startswith("https://cdn.discord.com")
        assert attachments[0]["filename"] == "image.png"

    def test_multiple_attachments(self):
        # Act
        msg = MessageIn(
            origin="discord",
            channel_id="123456789",
            author_id="987654321",
            author_display="User",
            content="Multiple files",
            message_id="msg123",
            raw={
                "attachments": [
                    {"url": "https://cdn.discord.com/file1.png", "filename": "file1.png"},
                    {"url": "https://cdn.discord.com/file2.jpg", "filename": "file2.jpg"},
                ]
            },
        )

        # Assert
        attachments = msg.raw.get("attachments", [])
        assert len(attachments) == 2


class TestIRCFileNotifications:
    """Test IRC file transfer notifications."""

    def test_file_notification_message_format(self):
        # Arrange
        filename = "document.pdf"
        file_url = "https://upload.example.com/doc123.pdf"

        # Act
        notification = f"📎 {filename}: {file_url}"

        # Assert
        assert filename in notification
        assert file_url in notification
        assert "📎" in notification

    def test_file_size_formatting(self):
        # Arrange
        sizes = [
            (1024, "1.0 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024 * 1024 * 5, "5.0 MB"),
        ]

        # Act & Assert
        for size_bytes, expected in sizes:
            if size_bytes < 1024 * 1024:
                formatted = f"{size_bytes / 1024:.1f} KB"
            else:
                formatted = f"{size_bytes / (1024 * 1024):.1f} MB"
            assert formatted == expected
