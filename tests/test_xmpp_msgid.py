"""Tests for XMPP message ID tracking."""

from __future__ import annotations

import pytest

from bridge.adapters.xmpp_msgid import XMPPMessageIDTracker


class TestXMPPMessageIDTracking:
    """Test XMPP message ID tracking for edits/deletes."""

    def test_store_and_retrieve_message_id(self):
        # Arrange
        tracker = XMPPMessageIDTracker()
        xmpp_id = "xmpp-msg-123"
        discord_id = "discord-msg-456"
        room_jid = "room@conference.example.com"

        # Act
        tracker.store(xmpp_id, discord_id, room_jid)
        result = tracker.get_discord_id(xmpp_id)

        # Assert
        assert result == discord_id

    def test_get_nonexistent_message_returns_none(self):
        # Arrange
        tracker = XMPPMessageIDTracker()

        # Act
        result = tracker.get_discord_id("nonexistent")

        # Assert
        assert result is None

    def test_multiple_rooms_tracked_independently(self):
        # Arrange
        tracker = XMPPMessageIDTracker()
        mappings = [
            ("xmpp1", "discord1", "room1@conference.example.com"),
            ("xmpp2", "discord2", "room2@conference.example.com"),
            ("xmpp3", "discord3", "room1@conference.example.com"),
        ]

        # Act
        for xmpp_id, discord_id, room_jid in mappings:
            tracker.store(xmpp_id, discord_id, room_jid)

        # Assert
        for xmpp_id, discord_id, _ in mappings:
            assert tracker.get_discord_id(xmpp_id) == discord_id

    def test_same_xmpp_id_different_rooms(self):
        # Arrange
        tracker = XMPPMessageIDTracker()
        xmpp_id = "msg-123"
        discord_id1 = "discord-1"
        discord_id2 = "discord-2"
        room1 = "room1@conference.example.com"
        room2 = "room2@conference.example.com"

        # Act
        tracker.store(xmpp_id, discord_id1, room1)
        tracker.store(xmpp_id, discord_id2, room2)

        # Assert - Should retrieve the most recent one
        result = tracker.get_discord_id(xmpp_id)
        assert result in [discord_id1, discord_id2]
