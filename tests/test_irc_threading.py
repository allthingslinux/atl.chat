"""Tests for IRC reply threading with draft/reply capability."""

from __future__ import annotations

import pytest

from bridge.adapters.irc_msgid import MessageIDTracker


class TestIRCReplyThreading:
    """Test IRC draft/reply message threading."""

    def test_message_id_stored_and_retrieved(self):
        # Arrange
        tracker = MessageIDTracker()
        discord_id = "123456789"
        irc_msgid = "abc123"

        # Act
        tracker.store(irc_msgid, discord_id)
        result = tracker.get_irc_msgid(discord_id)

        # Assert
        assert result == irc_msgid

    def test_message_id_returns_none_when_not_found(self):
        # Arrange
        tracker = MessageIDTracker()

        # Act
        result = tracker.get_irc_msgid("nonexistent")

        # Assert
        assert result is None

    def test_reverse_lookup_discord_from_irc_msgid(self):
        # Arrange
        tracker = MessageIDTracker()
        discord_id = "123456789"
        irc_msgid = "abc123"

        # Act
        tracker.store(irc_msgid, discord_id)
        result = tracker.get_discord_id(irc_msgid)

        # Assert
        assert result == discord_id

    def test_reverse_lookup_returns_none_when_not_found(self):
        # Arrange
        tracker = MessageIDTracker()

        # Act
        result = tracker.get_discord_id("nonexistent")

        # Assert
        assert result is None

    def test_multiple_messages_tracked_independently(self):
        # Arrange
        tracker = MessageIDTracker()
        pairs = [
            ("discord1", "irc1"),
            ("discord2", "irc2"),
            ("discord3", "irc3"),
        ]

        # Act
        for discord_id, irc_msgid in pairs:
            tracker.store(irc_msgid, discord_id)

        # Assert
        for discord_id, irc_msgid in pairs:
            assert tracker.get_irc_msgid(discord_id) == irc_msgid
            assert tracker.get_discord_id(irc_msgid) == discord_id
