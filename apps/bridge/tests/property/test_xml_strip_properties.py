"""Property-based tests for invalid XML character stripping (CP17).

**Validates: Requirement 16.1**

Property CP17: Invalid XML Character Stripping
  For any input string, after stripping invalid XML 1.0 characters, the result
  shall contain no invalid XML 1.0 characters.  All valid characters from the
  input are preserved, and the function is idempotent.
"""

from __future__ import annotations

from bridge.formatting.primitives import strip_invalid_xml_chars
from hypothesis import given, settings
from hypothesis import strategies as st


def is_valid_xml_char(c: str) -> bool:
    """Return True if *c* is a valid XML 1.0 character.

    Valid XML 1.0 chars:
      #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
    """
    cp = ord(c)
    return cp in {0x9, 0xA, 0xD} or (0x20 <= cp <= 0xD7FF) or (0xE000 <= cp <= 0xFFFD) or (0x10000 <= cp <= 0x10FFFF)


# Strategy: arbitrary text strings covering the full Unicode range.
_strings = st.text(min_size=0, max_size=300)


class TestXmlStripProperties:
    """**Validates: Requirement 16.1**"""

    @given(s=_strings)
    @settings(max_examples=200)
    def test_result_contains_no_invalid_xml_chars(self, s: str) -> None:
        """CP17: After stripping, every character in the result is valid XML 1.0.

        **Validates: Requirement 16.1**
        """
        result = strip_invalid_xml_chars(s)
        for i, c in enumerate(result):
            assert is_valid_xml_char(c), f"Invalid XML 1.0 char U+{ord(c):04X} at index {i} in result (input={s!r})"

    @given(s=_strings)
    @settings(max_examples=200)
    def test_valid_characters_preserved(self, s: str) -> None:
        """CP17: All valid XML 1.0 characters from the input appear in the output.

        **Validates: Requirement 16.1**
        """
        result = strip_invalid_xml_chars(s)
        expected = "".join(c for c in s if is_valid_xml_char(c))
        assert result == expected, f"Valid chars not preserved: expected {expected!r}, got {result!r} (input={s!r})"

    @given(s=_strings)
    @settings(max_examples=200)
    def test_idempotent(self, s: str) -> None:
        """CP17: Stripping twice yields the same result as stripping once.

        **Validates: Requirement 16.1**
        """
        once = strip_invalid_xml_chars(s)
        twice = strip_invalid_xml_chars(once)
        assert twice == once, f"Not idempotent: once={once!r}, twice={twice!r} (input={s!r})"
