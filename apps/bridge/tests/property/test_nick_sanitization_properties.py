"""Property-based tests for nick sanitization safety (CP9).

**Validates: Requirements 14.2, 14.3**

Property CP9: Nick Sanitization Safety
  For any input nick, ``sanitize_nick(nick)`` shall produce a non-empty string
  of at most 23 characters that does not start with a digit, slash, dash,
  single quote, colon, hash, ampersand, at sign, percent, or plus, and
  contains none of the forbidden characters (space, comma, asterisk, question
  mark, exclamation mark, at sign, hash, colon, slash, backslash, dot, NUL,
  CR, LF).
"""

from __future__ import annotations

from bridge.identity.sanitize import (
    _FORBIDDEN_NICK_CHARS,
    _FORBIDDEN_START_CHARS,
    sanitize_nick,
)
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Arbitrary unicode strings — the function must handle anything.
_ARBITRARY_NICK = st.text(min_size=0, max_size=100)


# ---------------------------------------------------------------------------
# CP9: Nick Sanitization Safety
# ---------------------------------------------------------------------------


class TestNickSanitizationSafety:
    """sanitize_nick produces safe nicks for all inputs.

    **Validates: Requirements 14.2, 14.3**
    """

    @given(nick=_ARBITRARY_NICK)
    @settings(max_examples=200)
    def test_result_is_non_empty(self, nick: str) -> None:
        """Result is always non-empty.

        **Validates: Requirement 14.2**
        """
        result = sanitize_nick(nick)
        assert len(result) > 0, f"sanitize_nick({nick!r}) produced empty string"

    @given(nick=_ARBITRARY_NICK)
    @settings(max_examples=200)
    def test_result_length_at_most_23(self, nick: str) -> None:
        """Result length is at most 23 characters.

        **Validates: Requirement 14.2**
        """
        result = sanitize_nick(nick)
        assert len(result) <= 23, f"sanitize_nick({nick!r}) produced {len(result)}-char string: {result!r}"

    @given(nick=_ARBITRARY_NICK)
    @settings(max_examples=200)
    def test_no_forbidden_characters(self, nick: str) -> None:
        """Result contains none of the forbidden characters.

        Forbidden: space, comma, asterisk, question mark, exclamation mark,
        at sign, hash, colon, slash, backslash, dot, NUL, CR, LF.

        **Validates: Requirement 14.3**
        """
        result = sanitize_nick(nick)
        found = set(result) & _FORBIDDEN_NICK_CHARS
        assert not found, f"sanitize_nick({nick!r}) = {result!r} contains forbidden chars: {found!r}"

    @given(nick=_ARBITRARY_NICK)
    @settings(max_examples=200)
    def test_no_forbidden_start_character(self, nick: str) -> None:
        """Result does not start with a forbidden start character.

        Forbidden start: digit, slash, dash, single quote, colon, hash,
        ampersand, at sign, percent, plus, tilde, dollar.

        **Validates: Requirement 14.2**
        """
        result = sanitize_nick(nick)
        assert result[0] not in _FORBIDDEN_START_CHARS, (
            f"sanitize_nick({nick!r}) = {result!r} starts with forbidden char {result[0]!r}"
        )
