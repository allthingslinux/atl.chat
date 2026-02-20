"""Tests for cross-protocol message formatting."""

from __future__ import annotations

import pytest

from bridge.formatting.discord_to_irc import discord_to_irc
from bridge.formatting.irc_message_split import split_irc_message
from bridge.formatting.irc_to_discord import irc_to_discord


class TestDiscordToIrc:
    """Test Discord markdown stripping for IRC."""

    @pytest.mark.parametrize(
        "input,expected",
        [
            ("**bold**", "bold"),
            ("__bold__", "bold"),
            ("*italic*", "italic"),
            ("_italic_", "italic"),
            ("`code`", "code"),
            ("~~strike~~", "strike"),
            ("||spoiler||", "spoiler"),
            ("``double``", "double"),
        ],
    )
    def test_strips_markdown(self, input, expected):
        assert discord_to_irc(input) == expected

    def test_preserves_urls(self):
        text = "Check https://example.com/path and http://test.org"
        assert discord_to_irc(text) == text

    def test_preserves_url_with_underscores(self):
        text = "See https://example.com/foo_bar_baz"
        assert discord_to_irc(text) == text

    def test_empty(self):
        assert discord_to_irc("") == ""
        assert discord_to_irc("   ") == "   "

    def test_strips_code_block(self):
        assert discord_to_irc("```\ncode block\n```") == ""
        assert discord_to_irc("before ```x\ny``` after") == "before  after"
        assert discord_to_irc("```py\nprint(1)\n```") == ""

    def test_combined_formatting(self):
        assert discord_to_irc("**bold** and *italic* and `code`") == "bold and italic and code"

    def test_url_with_markdown_chars_preserved(self):
        text = "https://example.com/foo_bar*star"
        assert discord_to_irc(text) == text

    def test_markdown_around_url_stripped(self):
        text = "**bold** https://x.com **bold**"
        assert discord_to_irc(text) == "bold https://x.com bold"

    def test_empty_spoiler_unchanged(self):
        # Regex requires content between pipes; empty |||| stays unchanged
        assert discord_to_irc("||||") == "||||"

    def test_none_like_empty(self):
        assert discord_to_irc("") == ""

    def test_whitespace_only(self):
        assert discord_to_irc(" \t\n ") == " \t\n "


class TestIrcToDiscord:
    """Test IRC control code conversion to Discord markdown."""

    def test_bold(self):
        assert irc_to_discord("\x02bold\x02") == "**bold**"

    def test_italic(self):
        assert irc_to_discord("\x1ditalic\x1d") == "*italic*"

    def test_strips_colors(self):
        assert irc_to_discord("\x0312colored\x03") == "colored"

    def test_reset_closes_formatting(self):
        assert irc_to_discord("\x02bold\x0f") == "**bold**"

    def test_preserves_urls(self):
        text = "https://example.com/foo_bar"
        assert irc_to_discord(text) == text

    def test_empty(self):
        assert irc_to_discord("") == ""

    def test_underline(self):
        assert irc_to_discord("\x1funderline\x1f") == "__underline__"

    def test_hex_color_stripped(self):
        assert irc_to_discord("\x04ff0000red\x0f") == "red"
        assert irc_to_discord("\x04FFFFFFwhite") == "white"

    def test_escapes_markdown_chars(self):
        assert irc_to_discord("a*b") == "a\\*b"
        assert irc_to_discord("a_b") == "a\\_b"
        assert irc_to_discord("a`b") == "a\\`b"
        assert irc_to_discord("a~b") == "a\\~b"
        assert irc_to_discord("a|b") == "a\\|b"

    def test_unclosed_formatting_closed(self):
        assert irc_to_discord("\x02bold no close") == "**bold no close**"
        assert irc_to_discord("\x1ditalic no close") == "*italic no close*"

    def test_combined_bold_italic_underline(self):
        s = "\x02bold\x1ditalic\x1funder\x0f"
        out = irc_to_discord(s)
        assert "**" in out
        assert "*" in out
        assert "__" in out

    def test_color_fg_only_stripped(self):
        assert irc_to_discord("\x0312colored\x03") == "colored"

    def test_color_fg_bg_stripped(self):
        assert irc_to_discord("\x0304,12hello\x03") == "hello"

    def test_url_not_escaped(self):
        text = "https://example.com/foo_bar"
        assert "\\" not in irc_to_discord(text)

    def test_reset_while_underline_closes_underline(self):
        # RESET (\x0F) while underline is active should close it (line 100)
        result = irc_to_discord("\x1funder\x0fafter")
        assert result == "__under__after"

    def test_url_at_end_of_string_no_trailing_text(self):
        # URL at end: last_end == len(content), trailing branch not taken (line 36)
        text = "see https://example.com"
        result = irc_to_discord(text)
        assert "https://example.com" in result
        assert result.endswith("https://example.com")


class TestSplitIrcMessage:
    """Test IRC message splitting."""

    def test_short_content_unchanged(self):
        content = "Hello world"
        assert split_irc_message(content) == [content]

    def test_empty_returns_empty_list(self):
        assert split_irc_message("") == []

    def test_long_content_split(self):
        content = "A" * 500
        chunks = split_irc_message(content, max_bytes=100)
        assert len(chunks) >= 5
        assert "".join(chunks) == content
        for c in chunks:
            assert len(c.encode("utf-8")) <= 100

    def test_splits_at_word_boundary(self):
        content = "word " * 100  # 500 chars
        chunks = split_irc_message(content, max_bytes=100)
        for c in chunks:
            # Should not break mid-word
            if len(c) > 1 and not c.endswith(" "):
                assert " " not in c or c.strip() == ""

    def test_unicode_safe(self):
        content = "日本語" * 50  # Multi-byte chars
        chunks = split_irc_message(content, max_bytes=50)
        assert "".join(chunks) == content

    def test_exact_max_bytes_boundary(self):
        content = "x" * 100
        chunks = split_irc_message(content, max_bytes=100)
        assert chunks == [content]
        assert len(chunks[0].encode("utf-8")) == 100

    def test_just_over_max_splits(self):
        content = "x" * 101
        chunks = split_irc_message(content, max_bytes=100)
        assert len(chunks) == 2
        assert "".join(chunks) == content
        assert len(chunks[0].encode("utf-8")) <= 100
        assert len(chunks[1].encode("utf-8")) <= 100

    def test_long_word_no_spaces_splits_mid_word(self):
        content = "a" * 200
        chunks = split_irc_message(content, max_bytes=50)
        assert len(chunks) >= 4
        assert "".join(chunks) == content
        for c in chunks:
            assert len(c.encode("utf-8")) <= 50

    def test_multibyte_char_at_chunk_boundary_not_split(self):
        # 3-byte UTF-8 char (\u4e2d) placed so it straddles the max_bytes boundary
        # The splitter must back up to avoid splitting mid-char
        prefix = "a" * 49  # 49 bytes
        content = prefix + "\u4e2d" + "b"  # 49 + 3 + 1 = 53 bytes
        chunks = split_irc_message(content, max_bytes=50)
        for c in chunks:
            c.encode("utf-8")  # must not raise — no split mid-char
            assert len(c.encode("utf-8")) <= 50
        assert "".join(chunks) == content

    def test_splits_at_newline(self):
        content = "a" * 60 + "\n" + "b" * 60
        chunks = split_irc_message(content, max_bytes=50)
        assert "".join(chunks) == content
        for c in chunks:
            assert len(c.encode("utf-8")) <= 50

    def test_multibyte_at_boundary(self):
        content = "a" * 49 + "é"  # é is 2 bytes in UTF-8, total 51
        chunks = split_irc_message(content, max_bytes=50)
        assert "".join(chunks) == content
        for c in chunks:
            assert len(c.encode("utf-8")) <= 50

    def test_reconstruct_identity(self):
        content = "Hello world, this is a test message with multiple words."
        chunks = split_irc_message(content, max_bytes=20)
        assert "".join(chunks) == content

    def test_single_char_repeated(self):
        content = "x" * 500
        chunks = split_irc_message(content, max_bytes=100)
        assert "".join(chunks) == content
        assert all(len(c.encode("utf-8")) <= 100 for c in chunks)
