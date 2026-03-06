"""Property-based tests for Discord event type filtering (CP21).

**Validates: Requirements 9.10, 9.11**

Property CP21: Discord Event Type Filtering
  Only MessageType.default and MessageType.reply are relayed; all other
  message types are filtered out.  Only ReactionType.normal reactions are
  relayed; burst (super) reactions are filtered out.
"""

from __future__ import annotations

import discord
from bridge.adapters.discord.handlers import should_relay_message, should_relay_reaction
from discord.enums import ReactionType
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# All MessageType enum members
_ALL_MESSAGE_TYPES = st.sampled_from(list(discord.MessageType))

# Only the two relayable message types
_RELAYABLE_MESSAGE_TYPES = st.sampled_from([discord.MessageType.default, discord.MessageType.reply])

# Non-relayable message types (everything except default and reply)
_NON_RELAYABLE_MESSAGE_TYPES = st.sampled_from(
    [mt for mt in discord.MessageType if mt not in (discord.MessageType.default, discord.MessageType.reply)]
)

# All ReactionType enum members
_ALL_REACTION_TYPES = st.sampled_from(list(ReactionType))


# ---------------------------------------------------------------------------
# CP21 Property 1: Only default/reply messages are relayed
# ---------------------------------------------------------------------------


class TestMessageTypeFiltering:
    """Only MessageType.default and MessageType.reply pass the relay filter.

    **Validates: Requirements 9.10, 9.11**
    """

    @given(message_type=_RELAYABLE_MESSAGE_TYPES)
    @settings(max_examples=200)
    def test_relayable_types_accepted(self, message_type: discord.MessageType) -> None:
        """Default and reply message types are always relayed.

        **Validates: Requirements 9.10, 9.11**
        """
        assert should_relay_message(message_type) is True, f"MessageType.{message_type.name} should be relayed"

    @given(message_type=_NON_RELAYABLE_MESSAGE_TYPES)
    @settings(max_examples=200)
    def test_non_relayable_types_rejected(self, message_type: discord.MessageType) -> None:
        """All message types other than default/reply are filtered out.

        **Validates: Requirements 9.10, 9.11**
        """
        assert should_relay_message(message_type) is False, f"MessageType.{message_type.name} should NOT be relayed"

    @given(message_type=_ALL_MESSAGE_TYPES)
    @settings(max_examples=200)
    def test_relay_decision_is_boolean_partition(self, message_type: discord.MessageType) -> None:
        """For any MessageType, should_relay_message returns True iff type is default or reply.

        **Validates: Requirements 9.10, 9.11**
        """
        expected = message_type in (discord.MessageType.default, discord.MessageType.reply)
        assert should_relay_message(message_type) is expected


# ---------------------------------------------------------------------------
# CP21 Property 2: Only normal reactions are relayed
# ---------------------------------------------------------------------------


class TestReactionTypeFiltering:
    """Only ReactionType.normal passes the relay filter.

    **Validates: Requirements 9.10, 9.11**
    """

    @given(reaction_type=_ALL_REACTION_TYPES)
    @settings(max_examples=200)
    def test_only_normal_reactions_relayed(self, reaction_type: ReactionType) -> None:
        """For any ReactionType, should_relay_reaction returns True only for normal.

        **Validates: Requirements 9.10, 9.11**
        """
        expected = reaction_type is ReactionType.normal
        assert should_relay_reaction(reaction_type) is expected, (
            f"ReactionType.{reaction_type.name}: expected relay={expected}"
        )

    def test_normal_reaction_accepted(self) -> None:
        """ReactionType.normal is always relayed.

        **Validates: Requirements 9.10, 9.11**
        """
        assert should_relay_reaction(ReactionType.normal) is True

    def test_burst_reaction_rejected(self) -> None:
        """ReactionType.burst (super reactions) is always filtered out.

        **Validates: Requirements 9.10, 9.11**
        """
        assert should_relay_reaction(ReactionType.burst) is False
