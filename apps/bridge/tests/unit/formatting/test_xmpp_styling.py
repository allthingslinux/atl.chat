"""Tests for formatting/xmpp_styling.py — XEP-0393 parser/emitter and XEP-0394 emitter."""

from __future__ import annotations

from bridge.formatting.primitives import CodeBlock, FormattedText, Span, Style
from bridge.formatting.xmpp_styling import (
    emit_xep0393,
    emit_xep0394,
    parse_xep0393,
)

# ===================================================================
# XEP-0393 Parser
# ===================================================================


class TestParseXEP0393Basic:
    """Basic inline style parsing."""

    def test_empty_string(self):
        ft = parse_xep0393("")
        assert ft.plain == ""
        assert ft.spans == []

    def test_plain_text(self):
        ft = parse_xep0393("hello world")
        assert ft.plain == "hello world"
        assert ft.spans == []

    def test_bold(self):
        ft = parse_xep0393("hello *world*")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.BOLD)

    def test_italic(self):
        ft = parse_xep0393("hello _world_")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.ITALIC)

    def test_strikethrough(self):
        ft = parse_xep0393("hello ~world~")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.STRIKETHROUGH)

    def test_strikethrough_discord_style(self):
        """~~text~~ (Discord-style) is parsed as strikethrough for XMPP-origin content."""
        ft = parse_xep0393("hello ~~world~~")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.STRIKETHROUGH)

    def test_monospace(self):
        ft = parse_xep0393("hello `world`")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.MONOSPACE)

    def test_bold_at_start(self):
        ft = parse_xep0393("*bold* text")
        assert ft.plain == "bold text"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(0, 4, Style.BOLD)

    def test_multiple_styles(self):
        ft = parse_xep0393("*bold* and _italic_")
        assert ft.plain == "bold and italic"
        assert len(ft.spans) == 2
        assert ft.spans[0] == Span(0, 4, Style.BOLD)
        assert ft.spans[1] == Span(9, 15, Style.ITALIC)


class TestParseXEP0393Boundaries:
    """XEP-0393 word boundary and whitespace rules."""

    def test_no_whitespace_after_opener(self):
        """Opener followed by whitespace should not match."""
        ft = parse_xep0393("hello * world*")
        assert ft.plain == "hello * world*"
        assert ft.spans == []

    def test_no_whitespace_before_closer(self):
        """Closer preceded by whitespace should not match."""
        ft = parse_xep0393("hello *world *")
        assert ft.plain == "hello *world *"
        assert ft.spans == []

    def test_single_char_styled(self):
        """Single character between directives is valid."""
        ft = parse_xep0393("*a*")
        assert ft.plain == "a"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(0, 1, Style.BOLD)

    def test_closing_followed_by_punctuation(self):
        """Closing directive followed by punctuation is valid."""
        ft = parse_xep0393("*bold*, then more")
        assert ft.plain == "bold, then more"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(0, 4, Style.BOLD)

    def test_closing_at_end_of_string(self):
        """Closing directive at end of string is valid."""
        ft = parse_xep0393("*bold*")
        assert ft.plain == "bold"
        assert len(ft.spans) == 1

    def test_double_asterisk_not_bold(self):
        """Double asterisks are not XEP-0393 bold (that's Discord)."""
        ft = parse_xep0393("**notbold**")
        # The outer * should match as bold around "*notbold*"
        # but the inner content starts with *, which is non-whitespace, so it matches
        assert ft.plain == "*notbold*"
        assert len(ft.spans) == 1
        assert ft.spans[0].style == Style.BOLD


class TestParseXEP0393CodeBlocks:
    """Fenced code block parsing."""

    def test_code_block(self):
        content = "before\n```\ncode here\n```\nafter"
        ft = parse_xep0393(content)
        assert "before" in ft.plain
        assert "after" in ft.plain
        assert len(ft.code_blocks) == 1
        assert "code here" in ft.code_blocks[0].content

    def test_code_block_with_language(self):
        content = "```python\nprint('hi')\n```"
        ft = parse_xep0393(content)
        assert len(ft.code_blocks) == 1
        assert ft.code_blocks[0].language == "python"
        assert "print('hi')" in ft.code_blocks[0].content

    def test_code_block_priority_over_inline(self):
        """Code blocks take priority over inline styles."""
        content = "```\n*not bold*\n```"
        ft = parse_xep0393(content)
        assert len(ft.code_blocks) == 1
        assert ft.spans == []


class TestParseXEP0393MonospacePriority:
    """Backtick (monospace) takes priority over other inline styles."""

    def test_backtick_over_bold(self):
        ft = parse_xep0393("`*not bold*`")
        assert ft.plain == "*not bold*"
        assert len(ft.spans) == 1
        assert ft.spans[0].style == Style.MONOSPACE


# ===================================================================
# XEP-0393 Emitter
# ===================================================================


class TestEmitXEP0393:
    def test_plain_text(self):
        ft = FormattedText(plain="hello world")
        assert emit_xep0393(ft) == "hello world"

    def test_bold(self):
        ft = FormattedText(
            plain="hello world",
            spans=[Span(6, 11, Style.BOLD)],
        )
        assert emit_xep0393(ft) == "hello *world*"

    def test_italic(self):
        ft = FormattedText(
            plain="hello world",
            spans=[Span(6, 11, Style.ITALIC)],
        )
        assert emit_xep0393(ft) == "hello _world_"

    def test_strikethrough(self):
        ft = FormattedText(
            plain="hello world",
            spans=[Span(6, 11, Style.STRIKETHROUGH)],
        )
        assert emit_xep0393(ft) == "hello ~world~"

    def test_monospace(self):
        ft = FormattedText(
            plain="hello world",
            spans=[Span(6, 11, Style.MONOSPACE)],
        )
        assert emit_xep0393(ft) == "hello `world`"

    def test_underline_dropped(self):
        """UNDERLINE has no XEP-0393 equivalent — silently dropped."""
        ft = FormattedText(
            plain="hello world",
            spans=[Span(6, 11, Style.UNDERLINE)],
        )
        assert emit_xep0393(ft) == "hello world"

    def test_code_block(self):
        ft = FormattedText(
            plain="before after",
            code_blocks=[CodeBlock(language="py", content="x=1", start=7, end=7)],
        )
        result = emit_xep0393(ft)
        assert "```py\nx=1\n```" in result

    def test_multiple_spans(self):
        ft = FormattedText(
            plain="bold and italic",
            spans=[
                Span(0, 4, Style.BOLD),
                Span(9, 15, Style.ITALIC),
            ],
        )
        assert emit_xep0393(ft) == "*bold* and _italic_"

    def test_combined_bold_italic(self):
        ft = FormattedText(
            plain="both",
            spans=[Span(0, 4, Style.BOLD | Style.ITALIC)],
        )
        result = emit_xep0393(ft)
        assert "*" in result
        assert "_" in result


# ===================================================================
# XEP-0394 Emitter
# ===================================================================


class TestEmitXEP0394:
    def test_empty(self):
        ft = FormattedText(plain="hello")
        markup = emit_xep0394(ft)
        # No spans → empty markup element
        assert len(list(markup)) == 0

    def test_bold_produces_strong(self):
        ft = FormattedText(
            plain="hello world",
            spans=[Span(6, 11, Style.BOLD)],
        )
        markup = emit_xep0394(ft)
        spans = list(markup)
        assert len(spans) == 1
        span_xml = spans[0].xml
        assert span_xml.get("start") == "6"
        assert span_xml.get("end") == "11"
        strong = span_xml.find("{urn:xmpp:markup:0}strong")
        assert strong is not None

    def test_italic_produces_emphasis(self):
        ft = FormattedText(
            plain="hello world",
            spans=[Span(6, 11, Style.ITALIC)],
        )
        markup = emit_xep0394(ft)
        spans = list(markup)
        assert len(spans) == 1
        emphasis = spans[0].xml.find("{urn:xmpp:markup:0}emphasis")
        assert emphasis is not None

    def test_monospace_produces_code(self):
        ft = FormattedText(
            plain="hello world",
            spans=[Span(6, 11, Style.MONOSPACE)],
        )
        markup = emit_xep0394(ft)
        spans = list(markup)
        assert len(spans) == 1
        code = spans[0].xml.find("{urn:xmpp:markup:0}code")
        assert code is not None

    def test_strikethrough_produces_deleted(self):
        ft = FormattedText(
            plain="hello world",
            spans=[Span(6, 11, Style.STRIKETHROUGH)],
        )
        markup = emit_xep0394(ft)
        spans = list(markup)
        assert len(spans) == 1
        deleted = spans[0].xml.find("{urn:xmpp:markup:0}deleted")
        assert deleted is not None

    def test_underline_dropped(self):
        """UNDERLINE has no XEP-0394 equivalent — dropped."""
        ft = FormattedText(
            plain="hello world",
            spans=[Span(6, 11, Style.UNDERLINE)],
        )
        markup = emit_xep0394(ft)
        spans = list(markup)
        assert len(spans) == 0

    def test_combined_bold_italic(self):
        """Combined BOLD|ITALIC produces both strong and emphasis."""
        ft = FormattedText(
            plain="hello world",
            spans=[Span(6, 11, Style.BOLD | Style.ITALIC)],
        )
        markup = emit_xep0394(ft)
        spans = list(markup)
        assert len(spans) == 1
        span_xml = spans[0].xml
        assert span_xml.find("{urn:xmpp:markup:0}strong") is not None
        assert span_xml.find("{urn:xmpp:markup:0}emphasis") is not None

    def test_multiple_spans(self):
        ft = FormattedText(
            plain="bold and italic",
            spans=[
                Span(0, 4, Style.BOLD),
                Span(9, 15, Style.ITALIC),
            ],
        )
        markup = emit_xep0394(ft)
        spans = list(markup)
        assert len(spans) == 2

    def test_code_block_produces_bcode(self):
        ft = FormattedText(
            plain="code here",
            code_blocks=[CodeBlock(language=None, content="code here", start=0, end=9)],
        )
        markup = emit_xep0394(ft)
        # Should have a bcode element
        bcodes = markup.xml.findall("{urn:xmpp:markup:0}bcode")
        assert len(bcodes) == 1


# ===================================================================
# Round-trip: parse → emit → parse
# ===================================================================


class TestRoundTrip:
    def test_bold_roundtrip(self):
        original = "hello *world*"
        ft1 = parse_xep0393(original)
        emitted = emit_xep0393(ft1)
        ft2 = parse_xep0393(emitted)
        assert ft1.plain == ft2.plain
        assert ft1.spans == ft2.spans

    def test_italic_roundtrip(self):
        original = "hello _world_"
        ft1 = parse_xep0393(original)
        emitted = emit_xep0393(ft1)
        ft2 = parse_xep0393(emitted)
        assert ft1.plain == ft2.plain
        assert ft1.spans == ft2.spans

    def test_monospace_roundtrip(self):
        original = "hello `world`"
        ft1 = parse_xep0393(original)
        emitted = emit_xep0393(ft1)
        ft2 = parse_xep0393(emitted)
        assert ft1.plain == ft2.plain
        assert ft1.spans == ft2.spans

    def test_plain_text_roundtrip(self):
        original = "just plain text"
        ft1 = parse_xep0393(original)
        emitted = emit_xep0393(ft1)
        assert emitted == original
        ft2 = parse_xep0393(emitted)
        assert ft1.plain == ft2.plain
