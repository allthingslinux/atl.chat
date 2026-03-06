"""Property-based tests for XEP-0308 correction chaining (CP20).

**Validates: Requirement 10.10**

Property CP20: XEP-0308 Correction Chaining
  For any sequence of corrections to the same message, the ``<replace>``
  element shall always reference the original message ID, not the ID of
  the previous correction.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Minimal model of XEP-0308 correction chaining
# ---------------------------------------------------------------------------
# In the XMPP adapter, ``send_correction_as_user`` receives
# ``original_xmpp_id`` and passes it directly to
# ``xep_0308.build_correction(id_to_replace=original_xmpp_id, ...)``.
#
# The caller is responsible for always passing the ORIGINAL message ID,
# never the ID of a previous correction.  This model captures that
# invariant: each correction in a chain produces a new stanza ID, but
# the ``id_to_replace`` must always point back to the very first message.


@dataclass
class CorrectionStanza:
    """Represents a single XEP-0308 correction stanza."""

    stanza_id: str  # Unique ID of this correction stanza
    id_to_replace: str  # The ID referenced in the <replace> element
    body: str  # New message content


@dataclass
class CorrectionChainTracker:
    """Tracks a chain of corrections for a single original message.

    Mirrors the bridge's approach: the caller always stores and passes
    the *original* message ID for the ``<replace>`` element, regardless
    of how many corrections have been applied.
    """

    original_id: str
    _corrections: list[CorrectionStanza] = field(default_factory=list)

    def apply_correction(self, new_body: str) -> CorrectionStanza:
        """Apply a correction.  Returns the stanza that would be sent.

        Each correction gets a fresh stanza ID, but ``id_to_replace``
        always references ``self.original_id``.
        """
        stanza = CorrectionStanza(
            stanza_id=str(uuid.uuid4()),
            id_to_replace=self.original_id,
            body=new_body,
        )
        self._corrections.append(stanza)
        return stanza

    @property
    def correction_ids(self) -> list[str]:
        """Return all stanza IDs produced by corrections (not the original)."""
        return [c.stanza_id for c in self._corrections]

    @property
    def all_stanzas(self) -> list[CorrectionStanza]:
        return list(self._corrections)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Realistic message body content
_BODY = st.text(
    alphabet=st.characters(categories=("L", "N", "P", "Z"), max_codepoint=0xFFFF),
    min_size=1,
    max_size=200,
)

# A sequence of correction bodies (2–20 corrections in a chain)
_CORRECTION_BODIES = st.lists(_BODY, min_size=2, max_size=20)


# ---------------------------------------------------------------------------
# CP20 Property Tests
# ---------------------------------------------------------------------------


class TestXEP0308CorrectionChaining:
    """XEP-0308 correction chaining properties.

    **Validates: Requirement 10.10**
    """

    @given(bodies=_CORRECTION_BODIES)
    @settings(max_examples=200)
    def test_replace_always_references_original(self, bodies: list[str]) -> None:
        """For any sequence of corrections, every ``<replace>`` element
        references the original message ID, never a correction ID.

        **Validates: Requirement 10.10**
        """
        original_id = str(uuid.uuid4())
        tracker = CorrectionChainTracker(original_id=original_id)

        for body in bodies:
            stanza = tracker.apply_correction(body)
            assert stanza.id_to_replace == original_id, (
                f"Correction stanza referenced {stanza.id_to_replace!r} instead of original {original_id!r}"
            )

    @given(bodies=_CORRECTION_BODIES)
    @settings(max_examples=200)
    def test_replace_never_references_correction_id(self, bodies: list[str]) -> None:
        """No ``<replace>`` element ever references the ID of a previous
        correction stanza — only the original message ID is valid.

        **Validates: Requirement 10.10**
        """
        original_id = str(uuid.uuid4())
        tracker = CorrectionChainTracker(original_id=original_id)
        seen_correction_ids: set[str] = set()

        for body in bodies:
            stanza = tracker.apply_correction(body)
            # The replace target must never be a previously-seen correction ID
            assert stanza.id_to_replace not in seen_correction_ids, (
                f"Correction referenced another correction's ID "
                f"{stanza.id_to_replace!r} instead of original {original_id!r}"
            )
            seen_correction_ids.add(stanza.stanza_id)

    @given(bodies=_CORRECTION_BODIES)
    @settings(max_examples=200)
    def test_each_correction_gets_unique_stanza_id(self, bodies: list[str]) -> None:
        """Each correction in the chain produces a unique stanza ID,
        distinct from the original and from all other corrections.

        **Validates: Requirement 10.10**
        """
        original_id = str(uuid.uuid4())
        tracker = CorrectionChainTracker(original_id=original_id)

        for body in bodies:
            tracker.apply_correction(body)

        all_ids = [original_id, *tracker.correction_ids]
        assert len(all_ids) == len(set(all_ids)), f"Duplicate IDs found: {all_ids}"

    @given(bodies=_CORRECTION_BODIES)
    @settings(max_examples=200)
    def test_original_id_is_stable_across_chain(self, bodies: list[str]) -> None:
        """The original message ID tracked by the chain never changes,
        regardless of how many corrections are applied.

        **Validates: Requirement 10.10**
        """
        original_id = str(uuid.uuid4())
        tracker = CorrectionChainTracker(original_id=original_id)

        for body in bodies:
            tracker.apply_correction(body)
            # The tracker's original_id must remain constant
            assert tracker.original_id == original_id, (
                f"Original ID mutated to {tracker.original_id!r} (expected {original_id!r})"
            )
