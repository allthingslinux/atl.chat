"""Tests for formatting/primitives.py — shared types, regex, and irc_casefold."""

from __future__ import annotations

import pytest
from bridge.formatting.primitives import (
    FENCE_RE,
    URL_RE,
    ZWS_RE,
    CodeBlock,
    FormattedText,
    Span,
    Style,
    irc_casefold,
)

# ---------------------------------------------------------------------------
# Style enum
# ---------------------------------------------------------------------------


class TestStyle:
    def test_flag_members(self):
        assert Style.BOLD is not None
        assert Style.ITALIC is not None
        assert Style.UNDERLINE is not None
        assert Style.STRIKETHROUGH is not None
        assert Style.MONOSPACE is not None

    def test_flag_combination(self):
        combined = Style.BOLD | Style.ITALIC
        assert Style.BOLD in combined
        assert Style.ITALIC in combined
        assert Style.UNDERLINE not in combined

    def test_all_flags_distinct(self):
        members = [Style.BOLD, Style.ITALIC, Style.UNDERLINE, Style.STRIKETHROUGH, Style.MONOSPACE]
        values = [m.value for m in members]
        assert len(values) == len(set(values))


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


class TestDataclasses:
    def test_span_creation(self):
        s = Span(start=0, end=5, style=Style.BOLD)
        assert s.start == 0
        assert s.end == 5
        assert s.style == Style.BOLD

    def test_code_block_creation(self):
        cb = CodeBlock(language="python", content="print('hi')", start=0, end=20)
        assert cb.language == "python"
        assert cb.content == "print('hi')"

    def test_code_block_no_language(self):
        cb = CodeBlock(language=None, content="code", start=0, end=10)
        assert cb.language is None

    def test_formatted_text_defaults(self):
        ft = FormattedText(plain="hello")
        assert ft.plain == "hello"
        assert ft.spans == []
        assert ft.code_blocks == []

    def test_formatted_text_with_spans(self):
        ft = FormattedText(
            plain="hello world",
            spans=[Span(0, 5, Style.BOLD)],
            code_blocks=[],
        )
        assert len(ft.spans) == 1
        assert ft.spans[0].style == Style.BOLD


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------


class TestRegexPatterns:
    def test_url_re_matches_http(self):
        assert URL_RE.search("visit http://example.com today")

    def test_url_re_matches_https(self):
        assert URL_RE.search("visit https://example.com/path?q=1 today")

    def test_url_re_matches_parenthesized_urls(self):
        m = URL_RE.search("see https://en.wikipedia.org/wiki/Foo_(bar) here")
        assert m is not None
        assert "Foo_(bar)" in m.group(0)

    def test_url_re_no_match_plain_text(self):
        assert URL_RE.search("no urls here") is None

    def test_fence_re_matches_code_block(self):
        text = "before ```python\nprint('hi')\n``` after"
        m = FENCE_RE.search(text)
        assert m is not None
        assert "print('hi')" in m.group(0)

    def test_fence_re_no_match(self):
        assert FENCE_RE.search("no code blocks") is None

    def test_zws_re_matches(self):
        assert ZWS_RE.search("hello\u200bworld")

    def test_zws_re_no_match(self):
        assert ZWS_RE.search("hello world") is None


# ---------------------------------------------------------------------------
# irc_casefold
# ---------------------------------------------------------------------------


class TestIrcCasefold:
    # --- ascii mode ---
    def test_ascii_lowercases(self):
        assert irc_casefold("HELLO", "ascii") == "hello"

    def test_ascii_no_special_folding(self):
        assert irc_casefold("[test]", "ascii") == "[test]"
        assert irc_casefold("\\path", "ascii") == "\\path"
        assert irc_casefold("~user", "ascii") == "~user"

    # --- rfc1459 mode ---
    def test_rfc1459_lowercases(self):
        assert irc_casefold("HELLO", "rfc1459") == "hello"

    def test_rfc1459_folds_brackets(self):
        assert irc_casefold("[test]", "rfc1459") == "{test}"

    def test_rfc1459_folds_backslash(self):
        assert irc_casefold("\\path", "rfc1459") == "|path"

    def test_rfc1459_folds_tilde(self):
        assert irc_casefold("~user", "rfc1459") == "^user"

    def test_rfc1459_combined(self):
        assert irc_casefold("Nick[Away]\\~", "rfc1459") == "nick{away}|^"

    # --- rfc1459-strict mode ---
    def test_rfc1459_strict_folds_brackets(self):
        assert irc_casefold("[test]", "rfc1459-strict") == "{test}"

    def test_rfc1459_strict_folds_backslash(self):
        assert irc_casefold("\\path", "rfc1459-strict") == "|path"

    def test_rfc1459_strict_does_not_fold_tilde(self):
        assert irc_casefold("~user", "rfc1459-strict") == "~user"

    # --- idempotence ---
    def test_idempotent_ascii(self):
        s = "Hello[World]\\~"
        assert irc_casefold(irc_casefold(s, "ascii"), "ascii") == irc_casefold(s, "ascii")

    def test_idempotent_rfc1459(self):
        s = "Hello[World]\\~"
        assert irc_casefold(irc_casefold(s, "rfc1459"), "rfc1459") == irc_casefold(s, "rfc1459")

    def test_idempotent_rfc1459_strict(self):
        s = "Hello[World]\\~"
        result = irc_casefold(s, "rfc1459-strict")
        assert irc_casefold(result, "rfc1459-strict") == result

    # --- edge cases ---
    def test_empty_string(self):
        assert irc_casefold("", "ascii") == ""
        assert irc_casefold("", "rfc1459") == ""
        assert irc_casefold("", "rfc1459-strict") == ""

    def test_already_lowercase(self):
        assert irc_casefold("hello", "rfc1459") == "hello"

    def test_unknown_mapping_raises(self):
        with pytest.raises(ValueError, match="unknown casemapping"):
            irc_casefold("test", "unknown")

    def test_default_mapping_is_rfc1459(self):
        assert irc_casefold("[Test]") == irc_casefold("[Test]", "rfc1459")

    def test_lowercase_special_chars_unchanged_rfc1459(self):
        assert irc_casefold("{test}", "rfc1459") == "{test}"
        assert irc_casefold("|path", "rfc1459") == "|path"
        assert irc_casefold("^user", "rfc1459") == "^user"
