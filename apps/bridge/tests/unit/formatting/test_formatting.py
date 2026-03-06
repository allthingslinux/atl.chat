"""Tests for cross-protocol message formatting."""

from __future__ import annotations

from bridge.formatting.discord_to_xmpp import MarkupSpan, discord_to_xmpp
from bridge.formatting.splitter import extract_code_blocks, split_irc_message

# ---------------------------------------------------------------------------
# discord_to_xmpp
# ---------------------------------------------------------------------------


class TestDiscordToXmpp:
    """Test Discord markdown -> plain body + XEP-0394 spans."""

    def test_plain_text_no_spans(self):
        r = discord_to_xmpp("hello world")
        assert r.body == "hello world"
        assert r.spans == []
        assert r.styled_body is None

    def test_bold(self):
        r = discord_to_xmpp("**bold**")
        assert r.body == "bold"
        assert r.styled_body == "*bold*"
        assert r.spans == [MarkupSpan(0, 4, ["strong"])]

    def test_italic_asterisk(self):
        r = discord_to_xmpp("*italic*")
        assert r.body == "italic"
        assert r.styled_body == "_italic_"
        assert r.spans == [MarkupSpan(0, 6, ["emphasis"])]

    def test_italic_underscore(self):
        r = discord_to_xmpp("_italic_")
        assert r.body == "italic"
        assert r.styled_body == "_italic_"
        assert r.spans == [MarkupSpan(0, 6, ["emphasis"])]

    def test_bold_italic(self):
        r = discord_to_xmpp("***bold italic***")
        assert r.body == "bold italic"
        assert r.styled_body == "*_bold italic_*"
        assert r.spans == [MarkupSpan(0, 11, ["strong", "emphasis"])]

    def test_strikethrough(self):
        r = discord_to_xmpp("~~strike~~")
        assert r.body == "strike"
        assert r.styled_body == "~strike~"
        assert r.spans == [MarkupSpan(0, 6, ["deleted"])]

    def test_inline_code(self):
        r = discord_to_xmpp("`code`")
        assert r.body == "code"
        assert r.spans == [MarkupSpan(0, 4, ["code"])]

    def test_spoiler_stripped_no_span(self):
        r = discord_to_xmpp("||secret||")
        assert r.body == "secret"
        assert r.spans == []

    def test_underline_stripped_no_span(self):
        r = discord_to_xmpp("__underline__")
        assert r.body == "underline"
        assert r.spans == []

    def test_underline_bold_emits_strong(self):
        r = discord_to_xmpp("__**bold**__")
        assert r.body == "bold"
        assert r.styled_body == "*bold*"
        assert r.spans == [MarkupSpan(0, 4, ["strong"])]

    def test_underline_italic_emits_emphasis(self):
        r = discord_to_xmpp("__*italic*__")
        assert r.body == "italic"
        assert r.styled_body == "_italic_"
        assert r.spans == [MarkupSpan(0, 6, ["emphasis"])]

    def test_masked_link(self):
        r = discord_to_xmpp("[click here](https://example.com)")
        assert r.body == "click here (https://example.com)"
        assert r.spans == []

    def test_no_embed_url(self):
        r = discord_to_xmpp("<https://google.com>")
        assert r.body == "https://google.com"
        assert r.spans == []

    def test_no_embed_url_mid_sentence(self):
        r = discord_to_xmpp("check <https://google.com> out")
        assert r.body == "check https://google.com out"

    def test_header_stripped(self):
        r = discord_to_xmpp("# Hello world")
        assert r.body == "Hello world"

    def test_subtext_stripped(self):
        r = discord_to_xmpp("-# small")
        assert r.body == "small"

    def test_span_offset_mid_sentence(self):
        r = discord_to_xmpp("hello **world** end")
        assert r.body == "hello world end"
        assert r.spans == [MarkupSpan(6, 11, ["strong"])]

    def test_multiple_spans(self):
        r = discord_to_xmpp("**a** and *b*")
        assert r.body == "a and b"
        assert r.spans == [MarkupSpan(0, 1, ["strong"]), MarkupSpan(6, 7, ["emphasis"])]

    def test_fence_passthrough_no_spans(self):
        r = discord_to_xmpp("```\ncode\n```")
        assert "code" in r.body
        assert r.spans == []

    def test_empty(self):
        r = discord_to_xmpp("")
        assert r.body == ""
        assert r.spans == []

    def test_has_markup_true_when_spans(self):
        r = discord_to_xmpp("**bold**")
        assert r.has_markup is True

    def test_has_markup_false_when_plain(self):
        r = discord_to_xmpp("plain")
        assert r.has_markup is False


# ---------------------------------------------------------------------------
# extract_code_blocks
# ---------------------------------------------------------------------------


class TestExtractCodeBlocks:
    """Test fenced code block extraction for paste upload."""

    def test_no_blocks(self):
        r = extract_code_blocks("plain text")
        assert r.blocks == []
        assert r.text == "plain text"

    def test_block_no_lang(self):
        r = extract_code_blocks("```\nsome code\n```")
        assert len(r.blocks) == 1
        assert r.blocks[0].lang == ""
        assert r.blocks[0].content == "some code"
        assert r.text == "{PASTE_0}"

    def test_block_with_lang(self):
        r = extract_code_blocks("```python\nprint(1)\n```")
        assert r.blocks[0].lang == "python"
        assert r.blocks[0].content == "print(1)"

    def test_inline_fence_no_lang(self):
        r = extract_code_blocks("```some code```")
        assert r.blocks[0].lang == ""
        assert r.blocks[0].content == "some code"

    def test_inline_fence_in_sentence(self):
        r = extract_code_blocks("hey: ```some code``` done")
        assert r.blocks[0].content == "some code"
        assert r.text == "hey: {PASTE_0} done"

    def test_multiline_no_lang(self):
        r = extract_code_blocks("```\nline1\nline2\n```")
        assert r.blocks[0].content == "line1\nline2"

    def test_trailing_newline_stripped(self):
        r = extract_code_blocks("```\ncode\n```")
        assert not r.blocks[0].content.endswith("\n")

    def test_text_before_and_after(self):
        r = extract_code_blocks("before\n```\ncode\n```\nafter")
        assert r.text == "before\n{PASTE_0}\nafter"

    def test_multiple_blocks(self):
        r = extract_code_blocks("```\na\n```\nmid\n```\nb\n```")
        assert len(r.blocks) == 2
        assert r.blocks[0].content == "a"
        assert r.blocks[1].content == "b"
        assert r.text == "{PASTE_0}\nmid\n{PASTE_1}"

    def test_empty_string(self):
        r = extract_code_blocks("")
        assert r.blocks == []
        assert r.text == ""


# ---------------------------------------------------------------------------
# split_irc_message
# ---------------------------------------------------------------------------


class TestSplitIrcMessage:
    """Test IRC message splitting at byte boundaries."""

    def test_short_message_no_split(self):
        assert split_irc_message("Hello world") == ["Hello world"]

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
        content = "word " * 100
        chunks = split_irc_message(content, max_bytes=100)
        for c in chunks:
            assert len(c.encode("utf-8")) <= 100

    def test_unicode_safe(self):
        content = "\u65e5\u672c\u8a9e" * 50
        chunks = split_irc_message(content, max_bytes=50)
        assert "".join(chunks) == content

    def test_exact_max_bytes_boundary(self):
        content = "x" * 100
        chunks = split_irc_message(content, max_bytes=100)
        assert chunks == [content]

    def test_just_over_max_splits(self):
        content = "x" * 101
        chunks = split_irc_message(content, max_bytes=100)
        assert len(chunks) == 2
        assert "".join(chunks) == content

    def test_long_word_no_spaces(self):
        content = "a" * 200
        chunks = split_irc_message(content, max_bytes=50)
        assert "".join(chunks) == content
        assert all(len(c.encode("utf-8")) <= 50 for c in chunks)

    def test_multibyte_char_not_split(self):
        prefix = "a" * 49
        content = prefix + "\u4e2d" + "b"
        chunks = split_irc_message(content, max_bytes=50)
        for c in chunks:
            c.encode("utf-8")  # must not raise
            assert len(c.encode("utf-8")) <= 50
        assert "".join(chunks) == content

    def test_multibyte_at_boundary(self):
        content = "a" * 49 + "\u00e9"
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
