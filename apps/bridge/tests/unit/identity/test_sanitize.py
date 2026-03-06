"""Unit tests for identity/sanitize.py — webhook username and nick sanitization."""

from __future__ import annotations

from bridge.identity.sanitize import ensure_valid_username, sanitize_nick

# ---------------------------------------------------------------------------
# ensure_valid_username
# ---------------------------------------------------------------------------


class TestEnsureValidUsername:
    def test_normal_name(self):
        assert ensure_valid_username("Alice") == "Alice"

    def test_strips_whitespace(self):
        assert ensure_valid_username("  Bob  ") == "Bob"

    def test_empty_string_returns_fallback(self):
        result = ensure_valid_username("")
        assert 2 <= len(result) <= 32

    def test_single_char_returns_fallback(self):
        result = ensure_valid_username("A")
        assert len(result) >= 2

    def test_whitespace_only_returns_fallback(self):
        result = ensure_valid_username("   ")
        assert len(result) >= 2

    def test_truncates_long_name(self):
        result = ensure_valid_username("x" * 100)
        assert len(result) == 32

    def test_exactly_32_chars(self):
        result = ensure_valid_username("a" * 32)
        assert len(result) == 32
        assert result == "a" * 32

    def test_exactly_2_chars(self):
        result = ensure_valid_username("ab")
        assert result == "ab"


# ---------------------------------------------------------------------------
# sanitize_nick
# ---------------------------------------------------------------------------


class TestSanitizeNick:
    def test_normal_nick(self):
        assert sanitize_nick("alice") == "alice"

    def test_removes_spaces(self):
        assert sanitize_nick("a l i c e") == "alice"

    def test_removes_forbidden_chars(self):
        # space, comma, asterisk, question mark, exclamation, @, #, :, /, \, ., NUL, CR, LF
        assert sanitize_nick("a,b*c?d!e@f#g:h/i\\j.k") == "abcdefghijk"

    def test_removes_nul_cr_lf(self):
        assert sanitize_nick("a\x00b\rc\nd") == "abcd"

    def test_strips_forbidden_start_digit(self):
        assert sanitize_nick("123abc") == "abc"

    def test_strips_forbidden_start_dash(self):
        assert sanitize_nick("-abc") == "abc"

    def test_strips_forbidden_start_single_quote(self):
        assert sanitize_nick("'abc") == "abc"

    def test_strips_forbidden_start_tilde(self):
        assert sanitize_nick("~abc") == "abc"

    def test_strips_forbidden_start_dollar(self):
        assert sanitize_nick("$abc") == "abc"

    def test_strips_forbidden_start_plus(self):
        assert sanitize_nick("+abc") == "abc"

    def test_strips_forbidden_start_percent(self):
        assert sanitize_nick("%abc") == "abc"

    def test_truncates_to_23(self):
        result = sanitize_nick("a" * 50)
        assert len(result) == 23

    def test_custom_max_len(self):
        result = sanitize_nick("a" * 50, max_len=10)
        assert len(result) == 10

    def test_empty_returns_fallback(self):
        result = sanitize_nick("")
        assert result == "user"

    def test_all_forbidden_returns_fallback(self):
        result = sanitize_nick("@#:!*?")
        assert result == "user"

    def test_all_forbidden_start_chars_stripped(self):
        # After removing forbidden chars, only start-forbidden remain
        result = sanitize_nick("123")
        # digits are start-forbidden but not body-forbidden, so they get stripped from start
        assert result == "user"

    def test_preserves_unicode(self):
        result = sanitize_nick("Ünïcödé")
        assert result == "Ünïcödé"

    def test_result_never_empty(self):
        result = sanitize_nick("\x00\r\n")
        assert len(result) > 0
