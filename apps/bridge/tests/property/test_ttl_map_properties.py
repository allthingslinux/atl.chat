"""Property-based tests for BidirectionalTTLMap consistency (CP4).

**Validates: Requirements 6.1, 6.2, 7.1, 7.2**

Property CP4: Bidirectional TTL Map Consistency
  For any key pair (k1, k2) stored, get_forward(k1) returns (k2, v)
  and get_reverse(k2) returns (k1, v) until TTL expires.
"""

from unittest.mock import patch

from bridge.tracking.base import BidirectionalTTLMap
from hypothesis import given, settings
from hypothesis import strategies as st

# Strategies: generate distinct key pairs and arbitrary string values.
# Keys are text strings of reasonable length; we filter to ensure k1 != k2
# so forward/reverse lookups are unambiguous.
_keys = st.text(min_size=1, max_size=50)
_values = st.text(max_size=50)


class TestBidirectionalTTLMapConsistency:
    """**Validates: Requirements 6.1, 6.2, 7.1, 7.2**"""

    @given(
        k1=_keys,
        k2=_keys,
        v=_values,
    )
    @settings(max_examples=200)
    def test_forward_lookup_returns_stored_pair(self, k1: str, k2: str, v: str) -> None:
        """CP4a: get_forward(k1) returns (k2, v) for any stored (k1, k2, v).

        **Validates: Requirements 6.1, 7.1**
        """
        m: BidirectionalTTLMap[str, str] = BidirectionalTTLMap(ttl_seconds=3600)
        m.store(k1, k2, v)
        result = m.get_forward(k1)
        assert result == (k2, v), f"get_forward({k1!r}) = {result!r}, expected ({k2!r}, {v!r})"

    @given(
        k1=_keys,
        k2=_keys,
        v=_values,
    )
    @settings(max_examples=200)
    def test_reverse_lookup_returns_stored_pair(self, k1: str, k2: str, v: str) -> None:
        """CP4b: get_reverse(k2) returns (k1, v) for any stored (k1, k2, v).

        **Validates: Requirements 6.1, 7.2**
        """
        m: BidirectionalTTLMap[str, str] = BidirectionalTTLMap(ttl_seconds=3600)
        m.store(k1, k2, v)
        result = m.get_reverse(k2)
        assert result == (k1, v), f"get_reverse({k2!r}) = {result!r}, expected ({k1!r}, {v!r})"

    @given(
        k1=_keys,
        k2=_keys,
        v=_values,
        ttl=st.integers(min_value=1, max_value=7200),
        elapsed=st.floats(min_value=0.01, max_value=14400),
    )
    @settings(max_examples=200)
    def test_ttl_expiry_removes_both_lookups(self, k1: str, k2: str, v: str, ttl: int, elapsed: float) -> None:
        """CP4c: After TTL expires, both get_forward and get_reverse return None.

        **Validates: Requirements 6.2, 7.1, 7.2**
        """
        now = 1_000_000.0  # fixed base time
        m: BidirectionalTTLMap[str, str] = BidirectionalTTLMap(ttl_seconds=ttl)

        with patch("bridge.tracking.base.time") as mock_time:
            mock_time.time.return_value = now
            m.store(k1, k2, v)

            mock_time.time.return_value = now + elapsed

            if elapsed > ttl:
                # Entry should be expired
                assert m.get_forward(k1) is None, f"get_forward({k1!r}) should be None after {elapsed}s (TTL={ttl}s)"
                assert m.get_reverse(k2) is None, f"get_reverse({k2!r}) should be None after {elapsed}s (TTL={ttl}s)"
            else:
                # Entry should still be alive
                assert m.get_forward(k1) == (k2, v), (
                    f"get_forward({k1!r}) should be ({k2!r}, {v!r}) at {elapsed}s (TTL={ttl}s)"
                )
                assert m.get_reverse(k2) == (k1, v), (
                    f"get_reverse({k2!r}) should be ({k1!r}, {v!r}) at {elapsed}s (TTL={ttl}s)"
                )


class TestBidirectionalTTLMapAliasConsistency:
    """Property CP5: TTL Map Alias Consistency.

    **Validates: Requirements 6.4, 6.5**
    """

    @given(
        k1=_keys,
        k2=_keys,
        v=_values,
        alias=_keys,
    )
    @settings(max_examples=200)
    def test_forward_alias_resolves_to_same_entry(self, k1: str, k2: str, v: str, alias: str) -> None:
        """CP5a: A forward alias resolves to the same (k2, v) as the primary key.

        **Validates: Requirement 6.4**
        """
        m: BidirectionalTTLMap[str, str] = BidirectionalTTLMap(ttl_seconds=3600)
        m.store(k1, k2, v)

        result = m.add_alias(alias, k1, forward=True)
        assert result is True

        primary_result = m.get_forward(k1)
        alias_result = m.get_forward(alias)
        assert alias_result == primary_result, (
            f"Forward alias {alias!r} returned {alias_result!r}, expected same as primary {k1!r}: {primary_result!r}"
        )

    @given(
        k1=_keys,
        k2=_keys,
        v=_values,
        alias=_keys,
    )
    @settings(max_examples=200)
    def test_reverse_alias_resolves_to_same_entry(self, k1: str, k2: str, v: str, alias: str) -> None:
        """CP5b: A reverse alias resolves to the same (k1, v) as the primary key.

        **Validates: Requirement 6.4**
        """
        m: BidirectionalTTLMap[str, str] = BidirectionalTTLMap(ttl_seconds=3600)
        m.store(k1, k2, v)

        result = m.add_alias(alias, k2, forward=False)
        assert result is True

        primary_result = m.get_reverse(k2)
        alias_result = m.get_reverse(alias)
        assert alias_result == primary_result, (
            f"Reverse alias {alias!r} returned {alias_result!r}, expected same as primary {k2!r}: {primary_result!r}"
        )

    @given(
        alias=_keys,
        nonexistent=_keys,
    )
    @settings(max_examples=200)
    def test_alias_for_nonexistent_key_returns_false(self, alias: str, nonexistent: str) -> None:
        """CP5c: add_alias for a non-existent primary returns False, map unchanged.

        **Validates: Requirement 6.5**
        """
        m: BidirectionalTTLMap[str, str] = BidirectionalTTLMap(ttl_seconds=3600)

        # Snapshot state before
        fwd_before = dict(m._forward)
        rev_before = dict(m._reverse)

        result = m.add_alias(alias, nonexistent, forward=True)
        assert result is False, (
            f"add_alias({alias!r}, {nonexistent!r}, forward=True) should return False for non-existent primary"
        )

        # Map should be unchanged
        assert dict(m._forward) == fwd_before, "Forward store was modified by failed add_alias"
        assert dict(m._reverse) == rev_before, "Reverse store was modified by failed add_alias"

        # Also test reverse direction
        result_rev = m.add_alias(alias, nonexistent, forward=False)
        assert result_rev is False, (
            f"add_alias({alias!r}, {nonexistent!r}, forward=False) should return False for non-existent primary"
        )

        assert dict(m._forward) == fwd_before, "Forward store was modified by failed reverse add_alias"
        assert dict(m._reverse) == rev_before, "Reverse store was modified by failed reverse add_alias"
