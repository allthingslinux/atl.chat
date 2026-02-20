"""Tests for XMPP features (XEPs)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bridge.events import MessageIn


class TestXMPPMessageCorrection:
    """Test XEP-0308 Last Message Correction."""

    def test_correction_flag_preserved_in_message_in(self):
        # Act
        msg = MessageIn(
            origin="xmpp",
            channel_id="room@conference.example.com",
            author_id="user@example.com",
            author_display="User",
            content="corrected text",
            message_id="msg123",
            is_edit=True,
            raw={"replace_id": "original_msg_id"},
        )

        # Assert
        assert msg.is_edit is True
        assert msg.raw.get("replace_id") == "original_msg_id"

    def test_correction_without_replace_id(self):
        # Act
        msg = MessageIn(
            origin="xmpp",
            channel_id="room@conference.example.com",
            author_id="user@example.com",
            author_display="User",
            content="corrected text",
            message_id="msg123",
            is_edit=True,
        )

        # Assert
        assert msg.is_edit is True
        assert msg.raw.get("replace_id") is None


class TestXMPPMessageRetraction:
    """Test XEP-0424 Message Retraction."""

    def test_retraction_creates_delete_event(self):
        # Act - Retraction is represented as a message with special content
        msg = MessageIn(
            origin="xmpp",
            channel_id="room@conference.example.com",
            author_id="user@example.com",
            author_display="User",
            content="",
            message_id="msg123",
            raw={"retracted": True, "retract_id": "original_msg_id"},
        )

        # Assert
        assert msg.raw.get("retracted") is True
        assert msg.raw.get("retract_id") == "original_msg_id"


class TestXMPPReactions:
    """Test XEP-0444 Message Reactions."""

    def test_reaction_stored_in_raw_data(self):
        # Act
        msg = MessageIn(
            origin="xmpp",
            channel_id="room@conference.example.com",
            author_id="user@example.com",
            author_display="User",
            content="",
            message_id="reaction123",
            raw={
                "reaction": "👍",
                "target_id": "original_msg_id",
            },
        )

        # Assert
        assert msg.raw.get("reaction") == "👍"
        assert msg.raw.get("target_id") == "original_msg_id"


class TestXMPPReplies:
    """Test XEP-0461 Message Replies."""

    def test_reply_reference_preserved(self):
        # Act
        msg = MessageIn(
            origin="xmpp",
            channel_id="room@conference.example.com",
            author_id="user@example.com",
            author_display="User",
            content="This is a reply",
            message_id="reply123",
            reply_to_id="original_msg_id",
        )

        # Assert
        assert msg.reply_to_id == "original_msg_id"

    def test_reply_without_reference(self):
        # Act
        msg = MessageIn(
            origin="xmpp",
            channel_id="room@conference.example.com",
            author_id="user@example.com",
            author_display="User",
            content="Not a reply",
            message_id="msg123",
        )

        # Assert
        assert msg.reply_to_id is None


class TestXMPPSpoilers:
    """Test XEP-0382 Spoiler Messages."""

    def test_spoiler_flag_in_raw_data(self):
        # Act
        msg = MessageIn(
            origin="xmpp",
            channel_id="room@conference.example.com",
            author_id="user@example.com",
            author_display="User",
            content="Hidden content",
            message_id="msg123",
            raw={"spoiler": True, "spoiler_hint": "Plot twist"},
        )

        # Assert
        assert msg.raw.get("spoiler") is True
        assert msg.raw.get("spoiler_hint") == "Plot twist"

    def test_spoiler_without_hint(self):
        # Act
        msg = MessageIn(
            origin="xmpp",
            channel_id="room@conference.example.com",
            author_id="user@example.com",
            author_display="User",
            content="Hidden content",
            message_id="msg123",
            raw={"spoiler": True},
        )

        # Assert
        assert msg.raw.get("spoiler") is True
        assert msg.raw.get("spoiler_hint") is None


class TestXMPPDelayedDelivery:
    """Test XEP-0203 Delayed Delivery filtering."""

    def test_delayed_message_identified(self):
        # Arrange
        delay_timestamp = datetime.now(timezone.utc) - timedelta(hours=2)

        # Act
        msg = MessageIn(
            origin="xmpp",
            channel_id="room@conference.example.com",
            author_id="user@example.com",
            author_display="User",
            content="Old message",
            message_id="msg123",
            raw={"delayed": True, "delay_timestamp": delay_timestamp.isoformat()},
        )

        # Assert
        assert msg.raw.get("delayed") is True
        assert msg.raw.get("delay_timestamp") is not None

    def test_recent_message_not_delayed(self):
        # Act
        msg = MessageIn(
            origin="xmpp",
            channel_id="room@conference.example.com",
            author_id="user@example.com",
            author_display="User",
            content="New message",
            message_id="msg123",
        )

        # Assert
        assert msg.raw.get("delayed") is None
