"""Tests for MessageIDResolver — unified cross-protocol message ID tracking."""

from __future__ import annotations

from unittest.mock import patch

from bridge.tracking.message_ids import MessageIDResolver


class TestMessageIDResolverBasic:
    """Core store / resolve / resolve_reverse behaviour."""

    def test_store_and_resolve(self) -> None:
        """Stored mapping is retrievable via resolve."""
        r = MessageIDResolver()
        r.store("discord", "irc", "d-1", "irc-1")
        assert r.resolve("discord", "irc", "d-1") == "irc-1"

    def test_store_and_resolve_reverse(self) -> None:
        """Stored mapping is retrievable via resolve_reverse."""
        r = MessageIDResolver()
        r.store("discord", "irc", "d-1", "irc-1")
        assert r.resolve_reverse("discord", "irc", "irc-1") == "d-1"

    def test_resolve_nonexistent_returns_none(self) -> None:
        """resolve returns None for unknown origin_id."""
        r = MessageIDResolver()
        assert r.resolve("discord", "irc", "nope") is None

    def test_resolve_reverse_nonexistent_returns_none(self) -> None:
        """resolve_reverse returns None for unknown target_id."""
        r = MessageIDResolver()
        assert r.resolve_reverse("discord", "irc", "nope") is None

    def test_store_with_value(self) -> None:
        """Optional value is stored alongside the mapping."""
        r = MessageIDResolver()
        r.store("discord", "xmpp", "d-1", "x-1", value="room@muc")
        # Value doesn't affect resolve — it returns the target_id.
        assert r.resolve("discord", "xmpp", "d-1") == "x-1"
        assert r.resolve_reverse("discord", "xmpp", "x-1") == "d-1"


class TestMessageIDResolverPairSymmetry:
    """Swapped protocol pair ordering uses the same underlying map."""

    def test_resolve_with_swapped_pair(self) -> None:
        """store(discord, irc, ...) is resolvable via resolve(irc, discord, ...)."""
        r = MessageIDResolver()
        r.store("discord", "irc", "d-1", "irc-1")
        # Swapped pair: irc→discord. origin_id is irc-1, target_id is d-1.
        assert r.resolve("irc", "discord", "irc-1") == "d-1"

    def test_resolve_reverse_with_swapped_pair(self) -> None:
        """store(discord, irc, ...) reverse-resolvable via swapped pair."""
        r = MessageIDResolver()
        r.store("discord", "irc", "d-1", "irc-1")
        assert r.resolve_reverse("irc", "discord", "d-1") == "irc-1"

    def test_store_from_both_directions(self) -> None:
        """Storing from both directions of the same pair works."""
        r = MessageIDResolver()
        r.store("discord", "irc", "d-1", "irc-1")
        r.store("irc", "discord", "irc-2", "d-2")
        assert r.resolve("discord", "irc", "d-1") == "irc-1"
        assert r.resolve("irc", "discord", "irc-2") == "d-2"


class TestMessageIDResolverMultiplePairs:
    """Each protocol pair gets its own independent map."""

    def test_independent_pairs(self) -> None:
        """discord↔irc and discord↔xmpp are independent."""
        r = MessageIDResolver()
        r.store("discord", "irc", "d-1", "irc-1")
        r.store("discord", "xmpp", "d-1", "x-1")
        assert r.resolve("discord", "irc", "d-1") == "irc-1"
        assert r.resolve("discord", "xmpp", "d-1") == "x-1"

    def test_all_three_pairs(self) -> None:
        """All three protocol pairs coexist."""
        r = MessageIDResolver()
        r.store("discord", "irc", "d-1", "irc-1")
        r.store("discord", "xmpp", "d-2", "x-2")
        r.store("irc", "xmpp", "irc-3", "x-3")
        assert r.resolve("discord", "irc", "d-1") == "irc-1"
        assert r.resolve("discord", "xmpp", "d-2") == "x-2"
        assert r.resolve("irc", "xmpp", "irc-3") == "x-3"


class TestMessageIDResolverTTL:
    """TTL expiry propagates through to the underlying maps."""

    def test_expired_entries_not_resolved(self) -> None:
        """Entries past TTL are not returned."""
        with patch("bridge.tracking.base.time") as mock_time:
            # store() calls time.time() once, resolve→_cleanup() calls once
            mock_time.time.side_effect = [1000.0, 2000.0]
            r = MessageIDResolver(ttl_seconds=1)
            r.store("discord", "irc", "d-1", "irc-1")
            # At t=2000, cutoff=1999; entry at t=1000 is expired.
            assert r.resolve("discord", "irc", "d-1") is None

    def test_fresh_entries_survive(self) -> None:
        """Entries within TTL are returned."""
        with patch("bridge.tracking.base.time") as mock_time:
            # store() calls time.time() once, resolve→_cleanup() calls once
            mock_time.time.side_effect = [1000.0, 1000.5]
            r = MessageIDResolver(ttl_seconds=3600)
            r.store("discord", "irc", "d-1", "irc-1")
            assert r.resolve("discord", "irc", "d-1") == "irc-1"


class TestMessageIDResolverOverwrite:
    """Overwriting an existing mapping."""

    def test_overwrite_updates_forward(self) -> None:
        """Storing the same origin_id again updates the target_id."""
        r = MessageIDResolver()
        r.store("discord", "irc", "d-1", "irc-old")
        r.store("discord", "irc", "d-1", "irc-new")
        assert r.resolve("discord", "irc", "d-1") == "irc-new"
