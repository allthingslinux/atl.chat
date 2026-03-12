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

    def test_add_discord_id_alias_enables_reaction_lookup(self) -> None:
        """add_discord_id_alias links Discord ID when IRC echo stored xmpp_id (XMPP-origin)."""
        tracker = MessageIDTracker()
        # Simulate IRC echo: irc_msgid -> xmpp_id (stored as discord_id in mapping)
        tracker.store("irc-msgid-abc", "xmpp-id-019cde19")
        assert tracker.get_irc_msgid("1481354198271529023") is None
        # Webhook returns; add real Discord ID as alias
        added = tracker.add_discord_id_alias("1481354198271529023", "xmpp-id-019cde19")
        assert added is True
        assert tracker.get_irc_msgid("1481354198271529023") == "irc-msgid-abc"

    def test_add_discord_id_alias_updates_get_discord_id_for_redact(self) -> None:
        """add_discord_id_alias updates irc_msgid->discord_id so REDACT→Discord delete works."""
        tracker = MessageIDTracker()
        # XMPP-origin: IRC echo stores irc_msgid -> xmpp_id
        tracker.store("irc-msgid-BXxmnc", "019cde86-4646-7bbd-8899-47c5795c8c03")
        assert tracker.get_discord_id("irc-msgid-BXxmnc") == "019cde86-4646-7bbd-8899-47c5795c8c03"
        # Discord webhook returns real snowflake; add_discord_id_alias updates mapping
        tracker.add_discord_id_alias("1481383997677506632", "019cde86-4646-7bbd-8899-47c5795c8c03")
        # get_discord_id must return real Discord ID for Discord delete API
        assert tracker.get_discord_id("irc-msgid-BXxmnc") == "1481383997677506632"

    def test_add_discord_id_alias_nonexistent_returns_false(self) -> None:
        """add_discord_id_alias returns False when existing_value not found."""
        tracker = MessageIDTracker()
        assert tracker.add_discord_id_alias("new-discord-id", "nonexistent-xmpp-id") is False

    def test_get_original_origin_irc_for_discord_snowflake(self) -> None:
        """get_original_origin returns 'irc' when stored with numeric Discord snowflake."""
        tracker = MessageIDTracker()
        tracker.store("irc-msg-1", "1481354198271529023")
        assert tracker.get_original_origin("irc-msg-1") == "irc"

    def test_get_original_origin_xmpp_for_ulid(self) -> None:
        """get_original_origin returns 'xmpp' when stored with XMPP ULID (XMPP-origin)."""
        tracker = MessageIDTracker()
        tracker.store("irc-msg-2", "019cde86-4646-7bbd-8899-47c5795c8c03")
        assert tracker.get_original_origin("irc-msg-2") == "xmpp"

    def test_get_original_origin_preserved_after_add_discord_id_alias(self) -> None:
        """get_original_origin stays 'xmpp' after add_discord_id_alias (XMPP-origin)."""
        tracker = MessageIDTracker()
        tracker.store("irc-msg-3", "019cde86-4646-7bbd-8899-47c5795c8c03")
        tracker.add_discord_id_alias("1481383997677506632", "019cde86-4646-7bbd-8899-47c5795c8c03")
        assert tracker.get_original_origin("irc-msg-3") == "xmpp"

    def test_get_original_origin_nonexistent_returns_none(self) -> None:
        """get_original_origin returns None for unknown msgid."""
        tracker = MessageIDTracker()
        assert tracker.get_original_origin("nonexistent") is None
