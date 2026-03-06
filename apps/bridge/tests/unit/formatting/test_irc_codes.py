"""Tests for formatting/irc_codes.py — IRC control code parser and emitter."""

from __future__ import annotations

import pytest
from bridge.formatting.irc_codes import (
    BOLD,
    COLOR,
    ITALIC,
    MONOSPACE,
    RESET,
    REVERSE,
    STRIKETHROUGH,
    UNDERLINE,
    detect_irc_spoilers,
    emit_irc_codes,
    parse_irc_codes,
)
from bridge.formatting.primitives import FormattedText, Span, Style

# ---------------------------------------------------------------------------
# Parser — basic toggle styles
# ---------------------------------------------------------------------------


class TestParseToggleStyles:
    def test_bold(self):
        ft = parse_irc_codes(f"hello {BOLD}world{BOLD}")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.BOLD)

    def test_italic(self):
        ft = parse_irc_codes(f"hello {ITALIC}world{ITALIC}")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.ITALIC)

    def test_underline(self):
        ft = parse_irc_codes(f"hello {UNDERLINE}world{UNDERLINE}")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.UNDERLINE)

    def test_strikethrough(self):
        ft = parse_irc_codes(f"hello {STRIKETHROUGH}world{STRIKETHROUGH}")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.STRIKETHROUGH)

    def test_monospace(self):
        ft = parse_irc_codes(f"hello {MONOSPACE}world{MONOSPACE}")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.MONOSPACE)

    def test_reverse_maps_to_italic(self):
        """Design decision D1: reverse (0x16) maps to Style.ITALIC."""
        ft = parse_irc_codes(f"hello {REVERSE}world{REVERSE}")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.ITALIC)


# ---------------------------------------------------------------------------
# Parser — reset
# ---------------------------------------------------------------------------


class TestParseReset:
    def test_reset_clears_all(self):
        ft = parse_irc_codes(f"{BOLD}bold{RESET} plain")
        assert ft.plain == "bold plain"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(0, 4, Style.BOLD)

    def test_reset_clears_multiple_styles(self):
        ft = parse_irc_codes(f"{BOLD}{ITALIC}both{RESET} plain")
        assert ft.plain == "both plain"
        assert len(ft.spans) == 1
        assert ft.spans[0].style == Style.BOLD | Style.ITALIC


# ---------------------------------------------------------------------------
# Parser — color codes
# ---------------------------------------------------------------------------


class TestParseColorCodes:
    def test_color_stripped(self):
        ft = parse_irc_codes(f"hello {COLOR}4red{COLOR} world")
        assert ft.plain == "hello red world"
        assert ft.spans == []

    def test_color_fg_bg_stripped(self):
        ft = parse_irc_codes(f"hello {COLOR}4,12colored{COLOR} world")
        assert ft.plain == "hello colored world"

    def test_color_no_digits(self):
        """Bare \\x03 with no digits resets color — treated as color reset."""
        ft = parse_irc_codes(f"hello {COLOR}world")
        assert ft.plain == "hello world"

    def test_color_with_formatting(self):
        ft = parse_irc_codes(f"{BOLD}bold {COLOR}4colored{COLOR}{BOLD}")
        assert ft.plain == "bold colored"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(0, 12, Style.BOLD)


# ---------------------------------------------------------------------------
# Parser — multiple and nested styles
# ---------------------------------------------------------------------------


class TestParseMultipleStyles:
    def test_bold_and_italic(self):
        ft = parse_irc_codes(f"{BOLD}bold{BOLD} {ITALIC}italic{ITALIC}")
        assert ft.plain == "bold italic"
        assert len(ft.spans) == 2
        assert ft.spans[0] == Span(0, 4, Style.BOLD)
        assert ft.spans[1] == Span(5, 11, Style.ITALIC)

    def test_overlapping_bold_italic(self):
        ft = parse_irc_codes(f"{BOLD}bo{ITALIC}th{BOLD}it{ITALIC}")
        assert ft.plain == "bothit"
        # "bo" = bold, "th" = bold|italic, "it" = italic
        assert len(ft.spans) == 3
        assert ft.spans[0] == Span(0, 2, Style.BOLD)
        assert ft.spans[1] == Span(2, 4, Style.BOLD | Style.ITALIC)
        assert ft.spans[2] == Span(4, 6, Style.ITALIC)


# ---------------------------------------------------------------------------
# Parser — edge cases
# ---------------------------------------------------------------------------


class TestParseEdgeCases:
    def test_empty_string(self):
        ft = parse_irc_codes("")
        assert ft.plain == ""
        assert ft.spans == []

    def test_plain_text(self):
        ft = parse_irc_codes("just plain text")
        assert ft.plain == "just plain text"
        assert ft.spans == []

    def test_unclosed_bold(self):
        """Unclosed formatting — span extends to end of text."""
        ft = parse_irc_codes(f"{BOLD}bold text")
        assert ft.plain == "bold text"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(0, 9, Style.BOLD)

    def test_empty_span_not_recorded(self):
        """Toggle on then immediately off produces no span."""
        ft = parse_irc_codes(f"hello{BOLD}{BOLD}world")
        assert ft.plain == "helloworld"
        assert ft.spans == []

    def test_consecutive_resets(self):
        ft = parse_irc_codes(f"{BOLD}text{RESET}{RESET}more")
        assert ft.plain == "textmore"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(0, 4, Style.BOLD)


# ---------------------------------------------------------------------------
# Spoiler detection
# ---------------------------------------------------------------------------


class TestDetectSpoilers:
    def test_fg_eq_bg_detected(self):
        content = f"hello {COLOR}1,1hidden{COLOR} world"
        ranges = detect_irc_spoilers(content)
        assert len(ranges) == 1
        # "hello " = 6 chars, "hidden" = 6 chars → range (6, 12)
        assert ranges[0] == (6, 12)

    def test_fg_neq_bg_not_detected(self):
        content = f"hello {COLOR}4,12colored{COLOR} world"
        ranges = detect_irc_spoilers(content)
        assert ranges == []

    def test_no_color_codes(self):
        ranges = detect_irc_spoilers("plain text")
        assert ranges == []

    def test_empty_string(self):
        ranges = detect_irc_spoilers("")
        assert ranges == []

    def test_spoiler_closed_by_reset(self):
        content = f"{COLOR}5,5secret{RESET} visible"
        ranges = detect_irc_spoilers(content)
        assert len(ranges) == 1
        assert ranges[0] == (0, 6)

    def test_multiple_spoiler_regions(self):
        content = f"{COLOR}1,1first{COLOR} gap {COLOR}2,2second{COLOR}"
        ranges = detect_irc_spoilers(content)
        assert len(ranges) == 2
        assert ranges[0] == (0, 5)
        # "first" = 5, " gap " = 5, "second" = 6 → second starts at 10
        assert ranges[1] == (10, 16)


# ---------------------------------------------------------------------------
# Emitter — basic styles
# ---------------------------------------------------------------------------


class TestEmitBasicStyles:
    def test_emit_bold(self):
        ft = FormattedText(plain="hello world", spans=[Span(6, 11, Style.BOLD)])
        result = emit_irc_codes(ft)
        assert result == f"hello {BOLD}world{BOLD}"

    def test_emit_italic(self):
        ft = FormattedText(plain="hello world", spans=[Span(6, 11, Style.ITALIC)])
        result = emit_irc_codes(ft)
        assert result == f"hello {ITALIC}world{ITALIC}"

    def test_emit_underline(self):
        ft = FormattedText(plain="hello world", spans=[Span(6, 11, Style.UNDERLINE)])
        result = emit_irc_codes(ft)
        assert result == f"hello {UNDERLINE}world{UNDERLINE}"

    def test_emit_strikethrough(self):
        ft = FormattedText(plain="hello world", spans=[Span(6, 11, Style.STRIKETHROUGH)])
        result = emit_irc_codes(ft)
        assert result == f"hello {STRIKETHROUGH}world{STRIKETHROUGH}"

    def test_emit_monospace(self):
        ft = FormattedText(plain="hello world", spans=[Span(6, 11, Style.MONOSPACE)])
        result = emit_irc_codes(ft)
        assert result == f"hello {MONOSPACE}world{MONOSPACE}"

    def test_emit_no_formatting(self):
        ft = FormattedText(plain="just text")
        assert emit_irc_codes(ft) == "just text"


# ---------------------------------------------------------------------------
# Emitter — combined styles
# ---------------------------------------------------------------------------


class TestEmitCombinedStyles:
    def test_emit_bold_italic(self):
        ft = FormattedText(
            plain="hello world",
            spans=[Span(6, 11, Style.BOLD | Style.ITALIC)],
        )
        result = emit_irc_codes(ft)
        assert result == f"hello {BOLD}{ITALIC}world{BOLD}{ITALIC}"

    def test_emit_multiple_spans(self):
        ft = FormattedText(
            plain="bold and italic",
            spans=[
                Span(0, 4, Style.BOLD),
                Span(9, 15, Style.ITALIC),
            ],
        )
        result = emit_irc_codes(ft)
        assert result == f"{BOLD}bold{BOLD} and {ITALIC}italic{ITALIC}"


# ---------------------------------------------------------------------------
# Round-trip: parse → emit → parse
# ---------------------------------------------------------------------------


class TestRoundTrip:
    @pytest.mark.parametrize(
        "irc_text",
        [
            f"hello {BOLD}world{BOLD}",
            f"hello {ITALIC}world{ITALIC}",
            f"hello {UNDERLINE}world{UNDERLINE}",
            f"hello {STRIKETHROUGH}world{STRIKETHROUGH}",
            f"hello {MONOSPACE}world{MONOSPACE}",
            f"{BOLD}bold{BOLD} and {ITALIC}italic{ITALIC}",
        ],
    )
    def test_parse_emit_roundtrip(self, irc_text: str):
        ft1 = parse_irc_codes(irc_text)
        emitted = emit_irc_codes(ft1)
        ft2 = parse_irc_codes(emitted)
        assert ft1.plain == ft2.plain
        assert ft1.spans == ft2.spans

    def test_plain_text_roundtrip(self):
        text = "no formatting here"
        ft = parse_irc_codes(text)
        assert emit_irc_codes(ft) == text
