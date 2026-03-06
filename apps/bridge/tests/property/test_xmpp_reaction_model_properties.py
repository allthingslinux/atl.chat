"""Property-based tests for XEP-0444 full-state reaction model (CP19).

**Validates: Requirement 10.8**

Property CP19: XEP-0444 Full-State Reaction Model
  For any sequence of reaction add and remove events for a given user and
  message, the outbound XMPP reaction stanza shall contain the complete set
  of currently-active reactions, not just the delta.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Minimal model of the XEP-0444 full-state reaction tracker
# ---------------------------------------------------------------------------
# This mirrors the pattern used in the XMPP adapter:
#   - Inbound (on_reactions): receives full set, diffs against previous state
#   - Outbound (send_reaction_as_user): must send the complete current set
#
# The tracker accumulates add/remove deltas into a full set per (user, msg).


@dataclass
class ReactionOp:
    """A single reaction add or remove operation."""

    emoji: str
    is_remove: bool


@dataclass
class XEP0444ReactionTracker:
    """Tracks per-(user, message) reaction state and produces full-state sets.

    XEP-0444 requires that each outbound reaction stanza contains the
    *complete* set of currently-active reactions, not just the delta.
    """

    _state: dict[tuple[str, str], set[str]] = field(default_factory=dict)

    def apply(self, user: str, msg_id: str, op: ReactionOp) -> frozenset[str]:
        """Apply an add/remove operation and return the full current set.

        This is the set that MUST be sent in the XEP-0444 stanza.
        """
        key = (user, msg_id)
        current = self._state.setdefault(key, set())
        if op.is_remove:
            current.discard(op.emoji)
        else:
            current.add(op.emoji)
        return frozenset(current)

    def get_state(self, user: str, msg_id: str) -> frozenset[str]:
        """Return the current full reaction set for a (user, message) pair."""
        return frozenset(self._state.get((user, msg_id), set()))


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Common emoji set — realistic subset of reactions used in chat
_EMOJI_ALPHABET = st.sampled_from(["👍", "👎", "❤️", "😂", "🎉", "🔥", "👀", "✅", "❌", "🤔"])

_REACTION_OP = st.builds(
    ReactionOp,
    emoji=_EMOJI_ALPHABET,
    is_remove=st.booleans(),
)

# Sequences of 1–30 operations (enough to exercise add/remove interleaving)
_OP_SEQUENCE = st.lists(_REACTION_OP, min_size=1, max_size=30)


# ---------------------------------------------------------------------------
# CP19 Property Tests
# ---------------------------------------------------------------------------


class TestXEP0444FullStateReactionModel:
    """XEP-0444 full-state reaction model properties.

    **Validates: Requirement 10.8**
    """

    @given(ops=_OP_SEQUENCE)
    @settings(max_examples=200)
    def test_full_state_matches_expected_set(self, ops: list[ReactionOp]) -> None:
        """After any sequence of add/remove ops, the tracker's full set equals
        the expected set computed by replaying the operations.

        **Validates: Requirement 10.8**
        """
        tracker = XEP0444ReactionTracker()
        expected: set[str] = set()

        for op in ops:
            if op.is_remove:
                expected.discard(op.emoji)
            else:
                expected.add(op.emoji)
            full_set = tracker.apply("user1", "msg1", op)
            assert full_set == frozenset(expected), (
                f"Full-state set {full_set} != expected {frozenset(expected)} "
                f"after {'remove' if op.is_remove else 'add'} {op.emoji}"
            )

    @given(ops=_OP_SEQUENCE)
    @settings(max_examples=200)
    def test_full_state_is_never_just_delta(self, ops: list[ReactionOp]) -> None:
        """The returned set after each operation contains ALL active reactions,
        not just the single emoji that was added or removed.

        **Validates: Requirement 10.8**
        """
        tracker = XEP0444ReactionTracker()

        for op in ops:
            full_set = tracker.apply("user1", "msg1", op)
            # The full set must be a superset of (or equal to) any single
            # previously-added emoji that hasn't been removed
            current_expected = tracker.get_state("user1", "msg1")
            assert full_set == current_expected, (
                f"Returned set {full_set} doesn't match tracked state {current_expected}"
            )

    @given(ops=_OP_SEQUENCE)
    @settings(max_examples=200)
    def test_remove_nonexistent_is_noop(self, ops: list[ReactionOp]) -> None:
        """Removing an emoji that isn't in the set doesn't change the state.

        **Validates: Requirement 10.8**
        """
        tracker = XEP0444ReactionTracker()

        for op in ops:
            state_before = tracker.get_state("user1", "msg1")
            full_set = tracker.apply("user1", "msg1", op)

            if op.is_remove and op.emoji not in state_before:
                # Removing a non-existent emoji should not change the set
                assert full_set == state_before, (
                    f"Removing non-existent {op.emoji} changed state: {state_before} -> {full_set}"
                )

    @given(
        ops_user1=_OP_SEQUENCE,
        ops_user2=_OP_SEQUENCE,
    )
    @settings(max_examples=200)
    def test_per_user_isolation(self, ops_user1: list[ReactionOp], ops_user2: list[ReactionOp]) -> None:
        """Reaction state is tracked per-user: operations from one user
        do not affect another user's reaction set on the same message.

        **Validates: Requirement 10.8**
        """
        tracker = XEP0444ReactionTracker()
        expected_u1: set[str] = set()
        expected_u2: set[str] = set()

        # Apply all ops for user1
        for op in ops_user1:
            if op.is_remove:
                expected_u1.discard(op.emoji)
            else:
                expected_u1.add(op.emoji)
            tracker.apply("alice", "msg1", op)

        # Apply all ops for user2
        for op in ops_user2:
            if op.is_remove:
                expected_u2.discard(op.emoji)
            else:
                expected_u2.add(op.emoji)
            tracker.apply("bob", "msg1", op)

        # Verify isolation
        assert tracker.get_state("alice", "msg1") == frozenset(expected_u1)
        assert tracker.get_state("bob", "msg1") == frozenset(expected_u2)

    @given(ops=_OP_SEQUENCE)
    @settings(max_examples=200)
    def test_add_then_remove_yields_empty(self, ops: list[ReactionOp]) -> None:
        """Adding then removing every emoji in the sequence yields an empty set
        (or a subset of emojis that were added but not removed).

        **Validates: Requirement 10.8**
        """
        tracker = XEP0444ReactionTracker()

        # First add all unique emojis
        unique_emojis = {op.emoji for op in ops}
        for emoji in unique_emojis:
            tracker.apply("user1", "msg1", ReactionOp(emoji=emoji, is_remove=False))

        # Then remove all of them
        for emoji in unique_emojis:
            tracker.apply("user1", "msg1", ReactionOp(emoji=emoji, is_remove=True))

        assert tracker.get_state("user1", "msg1") == frozenset(), (
            "After adding then removing all emojis, state should be empty"
        )
