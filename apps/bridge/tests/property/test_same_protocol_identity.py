"""Property-based tests for same-protocol identity conversion (CP14).

**Validates: Requirement 1.2**

Property CP14: Same-Protocol Identity Conversion
  For any content string and for any protocol, ``convert(content, protocol,
  protocol)`` shall return the content unchanged.  The converter short-circuits
  when origin equals target, so this holds for ALL content — including strings
  that contain formatting markers.
"""

from __future__ import annotations

from bridge.formatting.converter import ProtocolName, convert
from hypothesis import given, settings
from hypothesis import strategies as st

# All protocol names.
_protocols = st.sampled_from(["discord", "irc", "xmpp"])

# Arbitrary text content — intentionally unrestricted so we cover formatting
# markers, control codes, whitespace, emoji, etc.  Exclude surrogates (Cs)
# since they are not valid standalone characters in Python strings.
_content = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=0,
    max_size=200,
)


class TestSameProtocolIdentity:
    """CP14: Same-protocol conversion is the identity function.

    **Validates: Requirement 1.2**
    """

    @given(content=_content, protocol=_protocols)
    @settings(max_examples=200)
    def test_convert_same_protocol_returns_content_unchanged(
        self,
        content: str,
        protocol: ProtocolName,
    ) -> None:
        """convert(content, p, p) == content for all content and all protocols.

        **Validates: Requirement 1.2**
        """
        result = convert(content, protocol, protocol)
        assert result == content, (
            f"Same-protocol conversion altered content for {protocol}: input={content!r}, output={result!r}"
        )
