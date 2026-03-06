"""Tests for formatting/markdown.py — Discord markdown parser and emitter."""

from __future__ import annotations

import pytest
from bridge.formatting.markdown import emit_discord_markdown, parse_discord_markdown
from bridge.formatting.primitives import CodeBlock, FormattedText, Span, Style

# ---------------------------------------------------------------------------
# Parser — basic inline styles
# ---------------------------------------------------------------------------


class TestParseInlineStyles:
    def test_bold(self):
        ft = parse_discord_markdown("hello **world**")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.BOLD)

    def test_italic_asterisk(self):
        ft = parse_discord_markdown("hello *world*")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.ITALIC)

    def test_italic_underscore(self):
        ft = parse_discord_markdown("hello _world_")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.ITALIC)

    def test_underline(self):
        ft = parse_discord_markdown("hello __world__")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.UNDERLINE)

    def test_strikethrough(self):
        ft = parse_discord_markdown("hello ~~world~~")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.STRIKETHROUGH)

    def test_monospace_single_backtick(self):
        ft = parse_discord_markdown("hello `world`")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.MONOSPACE)

    def test_monospace_double_backtick(self):
        ft = parse_discord_markdown("hello ``world``")
        assert ft.plain == "hello world"
        assert len(ft.spans) == 1
        assert ft.spans[0] == Span(6, 11, Style.MONOSPACE)


# ---------------------------------------------------------------------------
# Parser — nested / combined styles
# ---------------------------------------------------------------------------


class TestParseNestedStyles:
    def test_bold_italic(self):
        ft = parse_discord_markdown("***bold italic***")
        assert ft.plain == "bold italic"
        assert len(ft.spans) == 1
        assert ft.spans[0].style == Style.BOLD | Style.ITALIC

    def test_multiple_spans(self):
        ft = parse_discord_markdown("**bold** and *italic*")
        assert ft.plain == "bold and italic"
        assert len(ft.spans) == 2
        assert ft.spans[0].style == Style.BOLD
        assert ft.spans[1].style == Style.ITALIC


# ---------------------------------------------------------------------------
# Parser — fenced code blocks
# ---------------------------------------------------------------------------


class TestParseCodeBlocks:
    def test_code_block_with_language(self):
        ft = parse_discord_markdown("before ```python\nprint('hi')\n``` after")
        assert "print('hi')" not in ft.plain
        assert ft.plain == "before  after"
        assert len(ft.code_blocks) == 1
        assert ft.code_blocks[0].language == "python"
        assert ft.code_blocks[0].content == "print('hi')\n"

    def test_code_block_no_language(self):
        ft = parse_discord_markdown("```\nsome code\n```")
        assert ft.plain == ""
        assert len(ft.code_blocks) == 1
        assert ft.code_blocks[0].language is None
        assert ft.code_blocks[0].content == "some code\n"

    def test_code_block_position(self):
        ft = parse_discord_markdown("abc ```js\nx\n``` def")
        # "abc " = 4 chars, code block at position 4, " def" follows
        assert ft.plain == "abc  def"
        assert ft.code_blocks[0].start == 4
        assert ft.code_blocks[0].end == 4

    def test_code_block_with_formatting_outside(self):
        ft = parse_discord_markdown("**bold** ```\ncode\n``` *italic*")
        assert ft.plain == "bold  italic"
        assert len(ft.spans) == 2
        assert ft.spans[0].style == Style.BOLD
        assert ft.spans[1].style == Style.ITALIC
        assert len(ft.code_blocks) == 1


# ---------------------------------------------------------------------------
# Parser — URL preservation
# ---------------------------------------------------------------------------


class TestParseURLPreservation:
    def test_url_not_modified(self):
        ft = parse_discord_markdown("visit https://example.com/path today")
        assert "https://example.com/path" in ft.plain

    def test_url_with_formatting_around(self):
        ft = parse_discord_markdown("**bold** https://example.com *italic*")
        assert "https://example.com" in ft.plain
        assert len(ft.spans) == 2

    def test_url_with_asterisks_not_parsed_as_formatting(self):
        ft = parse_discord_markdown("https://example.com/a*b*c")
        # The asterisks inside the URL should not be treated as italic
        assert "https://example.com/a*b*c" in ft.plain
        assert len(ft.spans) == 0


# ---------------------------------------------------------------------------
# Parser — edge cases
# ---------------------------------------------------------------------------


class TestParseEdgeCases:
    def test_empty_string(self):
        ft = parse_discord_markdown("")
        assert ft.plain == ""
        assert ft.spans == []
        assert ft.code_blocks == []

    def test_plain_text_no_formatting(self):
        ft = parse_discord_markdown("just plain text")
        assert ft.plain == "just plain text"
        assert ft.spans == []

    def test_backslash_escape(self):
        ft = parse_discord_markdown("not \\*italic\\*")
        assert ft.plain == "not *italic*"
        assert ft.spans == []


# ---------------------------------------------------------------------------
# Emitter — basic styles
# ---------------------------------------------------------------------------


class TestEmitBasicStyles:
    def test_emit_bold(self):
        ft = FormattedText(plain="hello world", spans=[Span(6, 11, Style.BOLD)])
        assert emit_discord_markdown(ft) == "hello **world**"

    def test_emit_italic(self):
        ft = FormattedText(plain="hello world", spans=[Span(6, 11, Style.ITALIC)])
        assert emit_discord_markdown(ft) == "hello *world*"

    def test_emit_underline(self):
        ft = FormattedText(plain="hello world", spans=[Span(6, 11, Style.UNDERLINE)])
        assert emit_discord_markdown(ft) == "hello __world__"

    def test_emit_strikethrough(self):
        ft = FormattedText(plain="hello world", spans=[Span(6, 11, Style.STRIKETHROUGH)])
        assert emit_discord_markdown(ft) == "hello ~~world~~"

    def test_emit_monospace(self):
        ft = FormattedText(plain="hello world", spans=[Span(6, 11, Style.MONOSPACE)])
        assert emit_discord_markdown(ft) == "hello `world`"

    def test_emit_bold_italic(self):
        ft = FormattedText(
            plain="hello world",
            spans=[Span(6, 11, Style.BOLD | Style.ITALIC)],
        )
        assert emit_discord_markdown(ft) == "hello ***world***"

    def test_emit_no_formatting(self):
        ft = FormattedText(plain="just text")
        assert emit_discord_markdown(ft) == "just text"


# ---------------------------------------------------------------------------
# Emitter — code blocks
# ---------------------------------------------------------------------------


class TestEmitCodeBlocks:
    def test_emit_code_block(self):
        ft = FormattedText(
            plain="before  after",
            code_blocks=[CodeBlock(language="python", content="x = 1\n", start=7, end=7)],
        )
        result = emit_discord_markdown(ft)
        assert "```python\nx = 1\n```" in result
        assert result.startswith("before ")
        assert result.endswith(" after")

    def test_emit_code_block_no_language(self):
        ft = FormattedText(
            plain="",
            code_blocks=[CodeBlock(language=None, content="code\n", start=0, end=0)],
        )
        result = emit_discord_markdown(ft)
        assert result == "```\ncode\n```"


# ---------------------------------------------------------------------------
# Round-trip: parse → emit → parse
# ---------------------------------------------------------------------------


class TestRoundTrip:
    @pytest.mark.parametrize(
        "md",
        [
            "hello **world**",
            "hello *world*",
            "hello __world__",
            "hello ~~world~~",
            "hello `world`",
            "***bold italic***",
            "**bold** and *italic*",
        ],
    )
    def test_parse_emit_roundtrip(self, md: str):
        ft1 = parse_discord_markdown(md)
        emitted = emit_discord_markdown(ft1)
        ft2 = parse_discord_markdown(emitted)
        assert ft1.plain == ft2.plain
        assert ft1.spans == ft2.spans

    def test_code_block_roundtrip(self):
        md = "before ```python\nprint('hi')\n``` after"
        ft1 = parse_discord_markdown(md)
        emitted = emit_discord_markdown(ft1)
        ft2 = parse_discord_markdown(emitted)
        assert ft1.plain == ft2.plain
        assert len(ft2.code_blocks) == 1
        assert ft2.code_blocks[0].language == ft1.code_blocks[0].language
        assert ft2.code_blocks[0].content == ft1.code_blocks[0].content
