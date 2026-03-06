"""Unit tests for BidirectionalTTLMap.

Validates Requirements 6.1-6.5:
  6.1 Bidirectional storage and retrieval
  6.2 TTL-based expiry
  6.3 Eviction when at capacity
  6.4 Alias resolution to same entry
  6.5 Alias for non-existent key returns False
"""

import time
from unittest.mock import patch

from bridge.tracking.base import BidirectionalTTLMap


class TestBidirectionalStorage:
    """Requirement 6.1: Bidirectional storage and retrieval."""

    def test_store_and_get_forward(self):
        m = BidirectionalTTLMap[str, str]()
        m.store("a", "b", "val")
        assert m.get_forward("a") == ("b", "val")

    def test_store_and_get_reverse(self):
        m = BidirectionalTTLMap[str, str]()
        m.store("a", "b", "val")
        assert m.get_reverse("b") == ("a", "val")

    def test_store_without_value(self):
        m = BidirectionalTTLMap[str, None]()
        m.store("a", "b")
        assert m.get_forward("a") == ("b", None)
        assert m.get_reverse("b") == ("a", None)

    def test_missing_key_returns_none(self):
        m = BidirectionalTTLMap[str, str]()
        assert m.get_forward("missing") is None
        assert m.get_reverse("missing") is None

    def test_overwrite_existing_key(self):
        m = BidirectionalTTLMap[str, str]()
        m.store("a", "b", "v1")
        m.store("a", "c", "v2")
        assert m.get_forward("a") == ("c", "v2")
        assert m.get_reverse("c") == ("a", "v2")


class TestTTLExpiry:
    """Requirement 6.2: TTL-based expiry."""

    def test_expired_entries_removed_on_get_forward(self):
        m = BidirectionalTTLMap[str, str](ttl_seconds=10)
        now = time.time()
        with patch("bridge.tracking.base.time") as mock_time:
            mock_time.time.return_value = now
            m.store("a", "b", "val")

            # Advance past TTL
            mock_time.time.return_value = now + 11
            assert m.get_forward("a") is None

    def test_expired_entries_removed_on_get_reverse(self):
        m = BidirectionalTTLMap[str, str](ttl_seconds=10)
        now = time.time()
        with patch("bridge.tracking.base.time") as mock_time:
            mock_time.time.return_value = now
            m.store("a", "b", "val")

            mock_time.time.return_value = now + 11
            assert m.get_reverse("b") is None

    def test_non_expired_entries_survive(self):
        m = BidirectionalTTLMap[str, str](ttl_seconds=10)
        now = time.time()
        with patch("bridge.tracking.base.time") as mock_time:
            mock_time.time.return_value = now
            m.store("a", "b", "val")

            mock_time.time.return_value = now + 5
            assert m.get_forward("a") == ("b", "val")


class TestEviction:
    """Requirement 6.3: Eviction when at capacity."""

    def test_evict_expired_when_full(self):
        m = BidirectionalTTLMap[str, str](ttl_seconds=10, maxsize=2)
        now = time.time()
        with patch("bridge.tracking.base.time") as mock_time:
            mock_time.time.return_value = now
            m.store("a", "b", "v1")

            # Advance so first entry expires
            mock_time.time.return_value = now + 11
            m.store("c", "d", "v2")
            m.store("e", "f", "v3")

            # Old entry should be gone, new ones present
            assert m.get_forward("a") is None
            assert m.get_forward("c") == ("d", "v2")
            assert m.get_forward("e") == ("f", "v3")

    def test_cleanup_triggered_at_maxsize(self):
        m = BidirectionalTTLMap[str, str](ttl_seconds=3600, maxsize=2)
        m.store("a", "b")
        m.store("c", "d")
        # At capacity — store triggers _evict_if_full which calls _cleanup
        # Since nothing is expired, all entries remain but no crash
        m.store("e", "f")
        assert m.get_forward("e") == ("f", None)


class TestAlias:
    """Requirements 6.4 and 6.5: Alias resolution."""

    def test_alias_resolves_to_same_entry(self):
        m = BidirectionalTTLMap[str, str]()
        m.store("a", "b", "val")
        assert m.add_alias("alias_a", "a", forward=True) is True
        assert m.get_forward("alias_a") == ("b", "val")

    def test_alias_in_reverse_store(self):
        m = BidirectionalTTLMap[str, str]()
        m.store("a", "b", "val")
        assert m.add_alias("alias_b", "b", forward=False) is True
        assert m.get_reverse("alias_b") == ("a", "val")

    def test_alias_shares_same_entry_object(self):
        m = BidirectionalTTLMap[str, str]()
        m.store("a", "b", "val")
        m.add_alias("alias_a", "a", forward=True)
        # Both should reference the same TTLEntry
        assert m._forward["a"] is m._forward["alias_a"]

    def test_alias_nonexistent_key_returns_false(self):
        m = BidirectionalTTLMap[str, str]()
        assert m.add_alias("alias", "nonexistent", forward=True) is False

    def test_alias_nonexistent_reverse_returns_false(self):
        m = BidirectionalTTLMap[str, str]()
        assert m.add_alias("alias", "nonexistent", forward=False) is False

    def test_alias_does_not_modify_map_on_failure(self):
        m = BidirectionalTTLMap[str, str]()
        m.add_alias("alias", "nonexistent", forward=True)
        assert m.get_forward("alias") is None
