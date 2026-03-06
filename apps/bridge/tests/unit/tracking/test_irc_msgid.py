"""Tests for IRC message ID tracking."""

from __future__ import annotations

from unittest.mock import patch

from bridge.adapters.irc import MessageIDTracker, MessageMapping


class TestMessageMapping:
    """Test MessageMapping NamedTuple."""

    def test_message_mapping_fields(self) -> None:
        """MessageMapping has irc_msgid, discord_id, timestamp."""
        m = MessageMapping(irc_msgid="irc-1", discord_id="discord-1", timestamp=1234.5)
        assert m.irc_msgid == "irc-1"
        assert m.discord_id == "discord-1"
        assert m.timestamp == 1234.5


class TestMessageIDTracker:
    """Test IRC message ID tracking for edits/deletes."""

    def test_store_and_get_discord_id(self) -> None:
        """Store mapping and retrieve Discord ID from IRC msgid."""
        tracker = MessageIDTracker()
        tracker.store("irc-msg-123", "discord-456")
        assert tracker.get_discord_id("irc-msg-123") == "discord-456"

    def test_store_and_get_irc_msgid(self) -> None:
        """Store mapping and retrieve IRC msgid from Discord ID."""
        tracker = MessageIDTracker()
        tracker.store("irc-msg-123", "discord-456")
        assert tracker.get_irc_msgid("discord-456") == "irc-msg-123"

    def test_get_discord_id_nonexistent_returns_none(self) -> None:
        """get_discord_id returns None for unknown IRC msgid."""
        tracker = MessageIDTracker()
        assert tracker.get_discord_id("nonexistent") is None

    def test_get_irc_msgid_nonexistent_returns_none(self) -> None:
        """get_irc_msgid returns None for unknown Discord ID."""
        tracker = MessageIDTracker()
        assert tracker.get_irc_msgid("nonexistent") is None

    def test_multiple_mappings_tracked_independently(self) -> None:
        """Multiple mappings can coexist."""
        tracker = MessageIDTracker()
        pairs = [("irc1", "discord1"), ("irc2", "discord2"), ("irc3", "discord3")]
        for irc_msgid, discord_id in pairs:
            tracker.store(irc_msgid, discord_id)
        for irc_msgid, discord_id in pairs:
            assert tracker.get_discord_id(irc_msgid) == discord_id
            assert tracker.get_irc_msgid(discord_id) == irc_msgid

    def test_overwrite_same_irc_msgid(self) -> None:
        """Storing same IRC msgid again overwrites forward mapping."""
        tracker = MessageIDTracker()
        tracker.store("irc-1", "discord-1")
        tracker.store("irc-1", "discord-2")
        assert tracker.get_discord_id("irc-1") == "discord-2"
        assert tracker.get_irc_msgid("discord-2") == "irc-1"

    def test_custom_ttl_seconds(self) -> None:
        """Tracker accepts custom TTL."""
        tracker = MessageIDTracker(ttl_seconds=60)
        assert tracker._ttl == 60

    def test_expired_entries_removed_on_get_discord_id(self) -> None:
        """Expired entries are removed when get_discord_id triggers _cleanup."""
        with patch("bridge.adapters.irc.msgid.time") as mock_time:
            mock_time.time.side_effect = [1000.0, 1002.0]  # store at 1000, get at 1002
            tracker = MessageIDTracker(ttl_seconds=1)
            tracker.store("irc-old", "discord-old")
            # At t=1002, cutoff=1001; mapping timestamp 1000 < 1001, so expired
            assert tracker.get_discord_id("irc-old") is None

    def test_expired_entries_removed_on_get_irc_msgid(self) -> None:
        """Expired entries are removed when get_irc_msgid triggers _cleanup."""
        with patch("bridge.adapters.irc.msgid.time") as mock_time:
            mock_time.time.side_effect = [1000.0, 1002.0]
            tracker = MessageIDTracker(ttl_seconds=1)
            tracker.store("irc-old", "discord-old")
            assert tracker.get_irc_msgid("discord-old") is None

    def test_fresh_entries_not_expired(self) -> None:
        """Entries within TTL are not removed."""
        with patch("bridge.adapters.irc.msgid.time") as mock_time:
            mock_time.time.side_effect = [
                1000.0,
                1000.5,
                1000.5,
            ]  # store, get_discord_id, get_irc_msgid
            tracker = MessageIDTracker(ttl_seconds=3600)
            tracker.store("irc-fresh", "discord-fresh")
            assert tracker.get_discord_id("irc-fresh") == "discord-fresh"
            assert tracker.get_irc_msgid("discord-fresh") == "irc-fresh"
