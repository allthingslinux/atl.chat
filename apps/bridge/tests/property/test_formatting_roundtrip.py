"""Property-based tests for formatting roundtrip preservation (CP1).

**Validates: Requirements 1.1, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8**

Property CP1: Formatting Roundtrip Preservation
  For plain text without formatting markers,
  strip_formatting(convert(t, origin, target), target) == t
  for all protocol pairs.
"""

from __future__ import annotations

from bridge.formatting.converter import ProtocolName, convert, strip_formatting
from hypothesis import assume, given, settings
from hypothesis import strategies as st

# Characters that act as formatting markers across all protocols.
# Discord: * _ ~ ` |
# IRC control codes: \x02 \x03 \x0f \x11 \x16 \x1d \x1e \x1f
# XEP-0393: * _ ~ `
_FORMATTING_MARKERS = frozenset("*_~`|\x02\x03\x0f\x11\x16\x1d\x1e\x1f")

# All protocol names.
_protocols = st.sampled_from(["discord", "irc", "xmpp"])

# Plain text strategy — arbitrary text up to 500 chars.
_plain_text = st.text(min_size=0, max_size=500)


def _has_no_formatting_markers(text: str) -> bool:
    """Return True when *text* contains no formatting markers for any protocol."""
    return not any(c in _FORMATTING_MARKERS for c in text)


class TestFormattingRoundtripPreservation:
    """CP1: Plain text survives conversion across all protocol pairs.

    **Validates: Requirements 1.1, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8**
    """

    @given(text=_plain_text, origin=_protocols, target=_protocols)
    @settings(max_examples=200)
    def test_plain_text_roundtrip(self, text: str, origin: ProtocolName, target: ProtocolName) -> None:
        """For plain text without formatting markers, converting from any
        origin to any target and stripping formatting yields the original text.

        **Validates: Requirements 1.1, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8**
        """
        assume(_has_no_formatting_markers(text))

        converted = convert(text, origin, target)
        stripped = strip_formatting(converted, target)
        assert stripped == text, (
            f"Roundtrip failed for {origin}→{target}: text={text!r}, converted={converted!r}, stripped={stripped!r}"
        )
