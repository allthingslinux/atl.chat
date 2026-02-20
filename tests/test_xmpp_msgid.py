"""Tests for XMPP message ID tracking."""

from __future__ import annotations

from unittest.mock import patch

from bridge.adapters.xmpp_msgid import XMPPMessageIDTracker, XMPPMessageMapping


class TestXMPPMessageMapping:
    """Test XMPPMessageMapping NamedTuple."""

    def test_xmpp_message_mapping_fields(self) -> None:
        """XMPPMessageMapping has xmpp_id, discord_id, room_jid, timestamp."""
        m = XMPPMessageMapping(
            xmpp_id="xmpp-1", discord_id="discord-1",
            room_jid="room@conf.example.com", timestamp=1234.5,
        )
        assert m.xmpp_id == "xmpp-1"
        assert m.discord_id == "discord-1"
        assert m.room_jid == "room@conf.example.com"
        assert m.timestamp == 1234.5


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

    def test_get_xmpp_id_retrieves_from_discord_id(self) -> None:
        """get_xmpp_id returns XMPP stanza ID from Discord message ID."""
        tracker = XMPPMessageIDTracker()
        tracker.store("xmpp-123", "discord-456", "room@conf.example.com")
        assert tracker.get_xmpp_id("discord-456") == "xmpp-123"

    def test_get_xmpp_id_nonexistent_returns_none(self) -> None:
        """get_xmpp_id returns None for unknown Discord ID."""
        tracker = XMPPMessageIDTracker()
        assert tracker.get_xmpp_id("nonexistent") is None

    def test_get_room_jid_retrieves_from_discord_id(self) -> None:
        """get_room_jid returns room JID from Discord message ID."""
        tracker = XMPPMessageIDTracker()
        tracker.store("xmpp-1", "discord-1", "muc@conference.example.com")
        assert tracker.get_room_jid("discord-1") == "muc@conference.example.com"

    def test_get_room_jid_nonexistent_returns_none(self) -> None:
        """get_room_jid returns None for unknown Discord ID."""
        tracker = XMPPMessageIDTracker()
        assert tracker.get_room_jid("nonexistent") is None

    def test_custom_ttl_seconds(self) -> None:
        """Tracker accepts custom TTL."""
        tracker = XMPPMessageIDTracker(ttl_seconds=120)
        assert tracker._ttl == 120

    def test_expired_entries_removed_on_get_discord_id(self) -> None:
        """Expired entries are removed when get_discord_id triggers _cleanup."""
        with patch("bridge.adapters.xmpp_msgid.time") as mock_time:
            mock_time.time.side_effect = [1000.0, 1002.0]
            tracker = XMPPMessageIDTracker(ttl_seconds=1)
            tracker.store("xmpp-old", "discord-old", "room@conf.example.com")
            assert tracker.get_discord_id("xmpp-old") is None

    def test_expired_entries_removed_on_get_xmpp_id(self) -> None:
        """Expired entries are removed when get_xmpp_id triggers _cleanup."""
        with patch("bridge.adapters.xmpp_msgid.time") as mock_time:
            mock_time.time.side_effect = [1000.0, 1002.0]
            tracker = XMPPMessageIDTracker(ttl_seconds=1)
            tracker.store("xmpp-old", "discord-old", "room@conf.example.com")
            assert tracker.get_xmpp_id("discord-old") is None

    def test_fresh_entries_not_expired(self) -> None:
        """Entries within TTL are not removed."""
        with patch("bridge.adapters.xmpp_msgid.time") as mock_time:
            mock_time.time.side_effect = [1000.0, 1000.5, 1000.5, 1000.5]
            tracker = XMPPMessageIDTracker(ttl_seconds=3600)
            tracker.store("xmpp-fresh", "discord-fresh", "room@conf.example.com")
            assert tracker.get_discord_id("xmpp-fresh") == "discord-fresh"
            assert tracker.get_xmpp_id("discord-fresh") == "xmpp-fresh"
            assert tracker.get_room_jid("discord-fresh") == "room@conf.example.com"

    def test_store_overwrites_existing_mapping(self) -> None:
        """Storing the same xmpp_id again replaces the old mapping in both dicts."""
        tracker = XMPPMessageIDTracker()
        tracker.store("xmpp-1", "discord-old", "room@conf.example.com")
        tracker.store("xmpp-1", "discord-new", "room@conf.example.com")
        assert tracker.get_discord_id("xmpp-1") == "discord-new"
        assert tracker.get_xmpp_id("discord-new") == "xmpp-1"

    def test_expired_room_jid_returns_none(self) -> None:
        """get_room_jid returns None for expired entries."""
        with patch("bridge.adapters.xmpp_msgid.time") as mock_time:
            mock_time.time.side_effect = [1000.0, 1002.0]
            tracker = XMPPMessageIDTracker(ttl_seconds=1)
            tracker.store("xmpp-1", "discord-1", "room@conf.example.com")
            assert tracker.get_room_jid("discord-1") is None

    def test_cleanup_removes_from_both_dicts(self) -> None:
        """_cleanup removes expired entries from both _xmpp_to_discord and _discord_to_xmpp."""
        with patch("bridge.adapters.xmpp_msgid.time") as mock_time:
            mock_time.time.side_effect = [1000.0, 1002.0]
            tracker = XMPPMessageIDTracker(ttl_seconds=1)
            tracker.store("xmpp-1", "discord-1", "room@conf.example.com")
            tracker._cleanup()
            assert "xmpp-1" not in tracker._xmpp_to_discord
            assert "discord-1" not in tracker._discord_to_xmpp
