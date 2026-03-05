"""Tests for cross-protocol message formatting."""

from __future__ import annotations

import pytest
from bridge.formatting.discord_to_irc import discord_to_irc
from bridge.formatting.discord_to_xmpp import MarkupSpan, discord_to_xmpp
from bridge.formatting.irc_message_split import extract_code_blocks, split_irc_message
from bridge.formatting.irc_to_discord import irc_to_discord
from bridge.formatting.irc_to_xmpp import irc_to_xmpp
from bridge.formatting.xmpp_to_discord import xmpp_to_discord
from bridge.formatting.xmpp_to_irc import xmpp_to_irc

# IRC formatting codes for readability in assertions
_B = "\x02"  # bold
_I = "\x1d"  # italic
_U = "\x1f"  # underline
_R = "\x0f"  # reset


# ---------------------------------------------------------------------------
# discord_to_irc
# ---------------------------------------------------------------------------


class TestDiscordToIrc:
    """Test Discord markdown → IRC formatting codes."""

    @pytest.mark.parametrize(
        "input,expected",
        [
            ("**bold**", f"{_B}bold{_B}"),
            ("__bold__", f"{_U}bold{_U}"),
            ("*italic*", f"{_I}italic{_I}"),
            ("_italic_", f"{_I}italic{_I}"),
            ("`code`", "\x11code\x11"),  # single backtick → IRC monospace
            ("~~strike~~", "\x1estrike\x1e"),  # IRC strikethrough \x1e
            ("||spoiler||", "\x0301,01spoiler\x03"),  # IRC black-on-black spoiler
            ("``double``", "\x11double\x11"),  # double → IRC monospace
        ],
    )
    def test_inline_formatting(self, input, expected):
        assert discord_to_irc(input) == expected

    def test_bold_italic_combined(self):
        assert discord_to_irc("***bold italic***") == f"{_B}{_I}bold italic{_I}{_B}"

    def test_underline_bold(self):
        assert discord_to_irc("__**bold**__") == f"{_U}{_B}bold{_B}{_U}"

    def test_underline_italic(self):
        assert discord_to_irc("__*italic*__") == f"{_U}{_I}italic{_I}{_U}"

    def test_masked_link(self):
        assert discord_to_irc("[click here](https://example.com)") == "click here (https://example.com)"

    def test_no_embed_url(self):
        assert discord_to_irc("<https://google.com>") == "https://google.com"

    def test_no_embed_url_mid_sentence(self):
        assert discord_to_irc("check <https://google.com> out") == "check https://google.com out"

    def test_masked_link_url_only(self):
        # When text equals the URL it still formats as "text (url)"
        assert discord_to_irc("[https://x.com](https://x.com)") == "https://x.com (https://x.com)"

    def test_header_h1_stripped(self):
        assert discord_to_irc("# Hello world") == "Hello world"

    def test_header_h2_stripped(self):
        assert discord_to_irc("## Hello world") == "Hello world"

    def test_header_h3_stripped(self):
        assert discord_to_irc("### Hello world") == "Hello world"

    def test_subtext_stripped(self):
        assert discord_to_irc("-# small text") == "small text"

    def test_header_mid_message_not_stripped(self):
        # # only stripped at start of line
        assert discord_to_irc("not a # header") == "not a # header"

    def test_combined_formatting(self):
        result = discord_to_irc("**bold** and *italic* and `code`")
        assert result == f"{_B}bold{_B} and {_I}italic{_I} and \x11code\x11"

    def test_preserves_bare_url(self):
        text = "Check https://example.com/path and http://test.org"
        assert discord_to_irc(text) == text

    def test_preserves_url_with_underscores(self):
        text = "See https://example.com/foo_bar_baz"
        assert discord_to_irc(text) == text

    def test_url_with_markdown_chars_preserved(self):
        text = "https://example.com/foo_bar*star"
        assert discord_to_irc(text) == text

    def test_markdown_around_url(self):
        text = "**bold** https://x.com **bold**"
        assert discord_to_irc(text) == f"{_B}bold{_B} https://x.com {_B}bold{_B}"

    def test_fence_preserved_for_paste_handler(self):
        assert discord_to_irc("```\ncode block\n```") == "```\ncode block\n```"
        assert discord_to_irc("before ```x\ny``` after") == "before ```x\ny``` after"
        assert discord_to_irc("```py\nprint(1)\n```") == "```py\nprint(1)\n```"

    def test_empty(self):
        assert discord_to_irc("") == ""

    def test_whitespace_only(self):
        assert discord_to_irc("   ") == "   "

    def test_empty_spoiler_unchanged(self):
        assert discord_to_irc("||||") == "||||"

    def test_multiline_header_only_first_line(self):
        result = discord_to_irc("# Title\nnormal text")
        assert result == "Title\nnormal text"

    def test_custom_emoji(self):
        assert discord_to_irc("<:wave:123456789>") == ":wave:"
        assert discord_to_irc("<a:dance:987654321>") == ":dance:"

    def test_user_mention(self):
        assert discord_to_irc("<@123456789>") == "@123456789"
        assert discord_to_irc("<@!123456789>") == "@123456789"

    def test_channel_mention(self):
        assert discord_to_irc("<#123456789>") == "#123456789"

    def test_role_mention(self):
        assert discord_to_irc("<@&123456789>") == "@123456789"

    def test_timestamp_stripped(self):
        assert discord_to_irc("<t:1234567890:F>") == ""
        assert discord_to_irc("<t:1234567890>") == ""

    def test_zero_width_space_stripped(self):
        assert discord_to_irc("he\u200bllo") == "hello"

    def test_underscore_in_word_not_italic(self):
        assert discord_to_irc("some_variable_name") == "some_variable_name"
        assert discord_to_irc("hello_world_foo") == "hello_world_foo"

    def test_underscore_italic_at_boundary(self):
        _I = "\x1d"
        assert discord_to_irc("_hello_ world") == f"{_I}hello{_I} world"

    def test_strikethrough_to_irc(self):
        assert discord_to_irc("~~strike~~") == "\x1estrike\x1e"

    def test_shrug_man(self):
        # ¯\_(ツ)_/¯ — the \_ is a Discord escape, result is ¯_(ツ)_/¯ (no italic)
        assert discord_to_irc("¯\\_(ツ)_/¯") == "¯_(ツ)_/¯"

    def test_spoiler_to_irc_black_on_black(self):
        assert discord_to_irc("||secret||") == "\x0301,01secret\x03"

    def test_spoiler_mid_sentence(self):
        assert discord_to_irc("before ||hidden|| after") == "before \x0301,01hidden\x03 after"

    def test_blockquote_to_curly_quotes(self):
        assert discord_to_irc("> hello world") == "\u201chello world\u201d"

    def test_blockquote_multiline(self):
        result = discord_to_irc("> line one\n> line two\nnormal")
        assert result == "\u201cline one\u201d\n\u201cline two\u201d\nnormal"

    def test_blockquote_mid_message_not_converted(self):
        # > only converted at start of line
        assert discord_to_irc("not a > quote") == "not a > quote"

    def test_multiline_blockquote_single_line(self):
        # >>> with a single line of content
        assert discord_to_irc(">>> hello world") == "\u201chello world\u201d"

    def test_multiline_blockquote_multiple_lines(self):
        # >>> captures everything to end of message
        result = discord_to_irc(">>> line one\nline two\nline three")
        assert result == "\u201cline one\u201d\n\u201cline two\u201d\n\u201cline three\u201d"

    def test_multiline_blockquote_with_text_before(self):
        # text before >>> is not quoted
        result = discord_to_irc("intro\n>>> quoted\nstill quoted")
        assert result == "intro\n\u201cquoted\u201d\n\u201cstill quoted\u201d"

    def test_multiline_blockquote_not_confused_with_single(self):
        # >>> should not be processed as > + leftover >>
        result = discord_to_irc(">>> only this")
        assert result == "\u201conly this\u201d"
        assert ">>" not in result


# ---------------------------------------------------------------------------
# discord_to_xmpp
# ---------------------------------------------------------------------------


class TestDiscordToXmpp:
    """Test Discord markdown → plain body + XEP-0394 spans."""

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
        # backtick is same in both — styled_body may be None (no change)
        assert r.spans == [MarkupSpan(0, 4, ["code"])]

    def test_spoiler_stripped_no_span(self):
        r = discord_to_xmpp("||secret||")
        assert r.body == "secret"
        assert r.spans == []

    def test_underline_stripped_no_span(self):
        # XEP-0394 has no underline type — markers stripped, no span emitted
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
        # Content should not have a trailing \n artifact
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
# xmpp_to_discord
# ---------------------------------------------------------------------------


class TestXmppToDiscord:
    """Test XEP-0393 Message Styling → Discord markdown."""

    def test_bold(self):
        assert xmpp_to_discord("*hello*") == "**hello**"

    def test_italic(self):
        assert xmpp_to_discord("_hello_") == "*hello*"

    def test_strikethrough(self):
        assert xmpp_to_discord("~hello~") == "~~hello~~"

    def test_mono(self):
        assert xmpp_to_discord("`code`") == "`code`"

    def test_pre_block_passthrough(self):
        assert xmpp_to_discord("```\nsome code\n```") == "```\nsome code\n```"

    def test_pre_block_opener_text_ignored(self):
        # XEP-0393: text after opening ``` is ignored; block still opens
        text = "```ignored\nsome code\n```"
        assert xmpp_to_discord(text) == text

    def test_pre_block_no_spans_inside(self):
        # Spans inside pre-blocks must NOT be converted
        text = "```\n*not bold*\n```"
        assert xmpp_to_discord(text) == text

    def test_text_before_pre_block(self):
        result = xmpp_to_discord("intro:\n```\ncode\n```")
        assert result.startswith("intro:")
        assert "```\ncode\n```" in result

    def test_text_after_pre_block(self):
        result = xmpp_to_discord("```\ncode\n```\noutro")
        assert result.endswith("outro")
        assert "```\ncode\n```" in result

    def test_mixed_inline(self):
        assert xmpp_to_discord("*bold* and _italic_") == "**bold** and *italic*"

    def test_multiple_bold_spans(self):
        assert xmpp_to_discord("*a* and *b*") == "**a** and **b**"

    def test_bold_italic_nested(self):
        # XEP-0393 bold+italic: *_text_* → ***text***
        assert xmpp_to_discord("*_bold italic_*") == "***bold italic***"

    def test_double_asterisk_not_bold_italic(self):
        # Regression: user types **word** in Dino — should be **word** (bold), not ***word***
        assert xmpp_to_discord("**word**") == "**word**"

    def test_double_asterisk_mid_sentence(self):
        # **text** in a sentence should not become bold+italic
        result = xmpp_to_discord("hello **world** end")
        assert result == "hello **world** end"

    def test_no_markup(self):
        assert xmpp_to_discord("plain text") == "plain text"

    def test_empty(self):
        assert xmpp_to_discord("") == ""

    def test_bold_not_italic_regression(self):
        # Key regression: Gajim *bold* must NOT arrive as Discord italic
        result = xmpp_to_discord("*bold text*")
        assert result == "**bold text**"

    def test_opener_followed_by_space_not_matched(self):
        # XEP-0393: opener must NOT be followed by whitespace
        assert xmpp_to_discord("* not bold*") == "* not bold*"

    def test_closer_preceded_by_space_not_matched(self):
        # XEP-0393: closer must NOT be preceded by whitespace
        assert xmpp_to_discord("*not bold *") == "*not bold *"

    def test_single_char_span(self):
        assert xmpp_to_discord("*x*") == "**x**"

    def test_quote_block_passthrough(self):
        # Block quotes pass through unchanged (Discord also renders > as quote)
        assert xmpp_to_discord("> quoted text") == "> quoted text"


# ---------------------------------------------------------------------------
# xmpp_to_irc
# ---------------------------------------------------------------------------


class TestXmppToIrc:
    """Test XEP-0393 Message Styling → IRC control codes."""

    _B = "\x02"
    _I = "\x1d"
    _S = "\x1e"
    _M = "\x11"

    def test_bold(self):
        assert xmpp_to_irc("*bold*") == f"{self._B}bold{self._B}"

    def test_double_asterisks_passthrough(self):
        # **text** → IRC bold (Discord-style bold, bridged to IRC \x02)
        assert xmpp_to_irc("**double asterisks from dino**") == f"{self._B}double asterisks from dino{self._B}"

    def test_double_underscore_passthrough(self):
        # __text__ → IRC underline (Discord-style underline, bridged to IRC \x1f)
        assert xmpp_to_irc("__double underscore from gajim__") == "\x1fdouble underscore from gajim\x1f"

    def test_italic(self):
        assert xmpp_to_irc("_italic_") == f"{self._I}italic{self._I}"

    def test_strikethrough(self):
        assert xmpp_to_irc("~strike~") == f"{self._S}strike{self._S}"

    def test_monospace(self):
        assert xmpp_to_irc("`mono`") == f"{self._M}mono{self._M}"

    def test_bold_italic_nested(self):
        assert xmpp_to_irc("*_bold italic_*") == f"{self._B}{self._I}bold italic{self._I}{self._B}"

    def test_opener_followed_by_space_not_matched(self):
        assert xmpp_to_irc("* not bold*") == "* not bold*"

    def test_closer_preceded_by_space_not_matched(self):
        assert xmpp_to_irc("*not bold *") == "*not bold *"

    def test_pre_block_passthrough(self):
        text = "```\nsome code\n```"
        assert xmpp_to_irc(text) == text

    def test_pre_block_no_spans_inside(self):
        text = "```\n*not bold*\n```"
        assert xmpp_to_irc(text) == text

    def test_mixed(self):
        assert xmpp_to_irc("*bold* and _italic_") == f"{self._B}bold{self._B} and {self._I}italic{self._I}"

    def test_plain_passthrough(self):
        assert xmpp_to_irc("plain text") == "plain text"

    def test_empty(self):
        assert xmpp_to_irc("") == ""

    def test_mono_contents_opaque(self):
        # Spans inside mono must NOT be converted
        assert xmpp_to_irc("`*not bold*`") == f"{self._M}*not bold*{self._M}"

    def test_blockquote_single_line(self):
        assert xmpp_to_irc("> greater than from gajim") == "\u201cgreater than from gajim\u201d"

    def test_blockquote_multiline(self):
        result = xmpp_to_irc("> line one\n> line two")
        assert result == "\u201cline one\u201d\n\u201cline two\u201d"

    def test_blockquote_with_inline_formatting(self):
        assert xmpp_to_irc("> *bold quote*") == f"\u201c{self._B}bold quote{self._B}\u201d"


# ---------------------------------------------------------------------------
# irc_to_discord
# ---------------------------------------------------------------------------


class TestIrcToDiscord:
    """Test IRC control code conversion to Discord markdown."""

    def test_bold(self):
        assert irc_to_discord(f"{_B}bold{_B}") == "**bold**"

    def test_italic(self):
        assert irc_to_discord(f"{_I}italic{_I}") == "*italic*"

    def test_underline(self):
        assert irc_to_discord(f"{_U}underline{_U}") == "__underline__"

    def test_strikethrough(self):
        assert irc_to_discord("\x1estrikethrough\x1e") == "~~strikethrough~~"

    def test_strikethrough_reset_closes(self):
        assert irc_to_discord("\x1estrike\x0fafter") == "~~strike~~after"

    def test_strikethrough_unclosed(self):
        assert irc_to_discord("\x1eno close") == "~~no close~~"

    def test_strips_colors(self):
        assert irc_to_discord("\x0312colored\x03") == "colored"

    def test_color_fg_bg_stripped(self):
        assert irc_to_discord("\x0304,12hello\x03") == "hello"

    def test_color_trailing_comma_preserved(self):
        # \x0304, with no bg digits — comma is literal text per spec
        assert irc_to_discord("\x0304,hello\x03") == ",hello"

    def test_hex_color_stripped(self):
        assert irc_to_discord("\x04ff0000red\x0f") == "red"
        assert irc_to_discord("\x04FFFFFFwhite") == "white"

    def test_reset_closes_formatting(self):
        assert irc_to_discord(f"{_B}bold{_R}") == "**bold**"

    def test_reset_closes_underline(self):
        assert irc_to_discord(f"{_U}under{_R}after") == "__under__after"

    def test_monospace(self):
        assert irc_to_discord("\x11mono\x11") == "`mono`"

    def test_monospace_unclosed(self):
        assert irc_to_discord("\x11mono") == "`mono`"

    def test_monospace_reset_closes(self):
        assert irc_to_discord("\x11mono\x0fafter") == "`mono`after"

    def test_reverse_stripped(self):
        # \x16 reverse has no Discord equivalent — silently stripped
        assert irc_to_discord("\x16text\x16") == "text"

    def test_reverse_mid_message(self):
        assert irc_to_discord("before\x16after") == "beforeafter"

    def test_preserves_urls(self):
        text = "https://example.com/foo_bar"
        assert irc_to_discord(text) == text

    def test_url_not_escaped(self):
        assert "\\" not in irc_to_discord("https://example.com/foo_bar")

    def test_spoiler_fg_eq_bg_to_discord(self):
        # IRC black-on-black \x0301,01 → Discord ||spoiler||
        assert irc_to_discord("\x0301,01secret\x03") == "||secret||"

    def test_spoiler_other_fg_eq_bg(self):
        # Any fg==bg pair is a spoiler
        assert irc_to_discord("\x0305,05hidden\x03") == "||hidden||"

    def test_non_spoiler_color_stripped(self):
        # fg != bg → just strip the color
        assert irc_to_discord("\x0304,12hello\x03") == "hello"

    def test_spoiler_round_trip(self):
        # Discord → IRC → Discord round-trip
        from bridge.formatting.discord_to_irc import discord_to_irc

        irc = discord_to_irc("||secret||")
        assert irc_to_discord(irc) == "||secret||"

    def test_url_at_end_of_string(self):
        text = "see https://example.com"
        result = irc_to_discord(text)
        assert result.endswith("https://example.com")

    def test_empty(self):
        assert irc_to_discord("") == ""

    def test_escapes_markdown_chars(self):
        # * and _ are intentionally NOT escaped — IRC users typing *text* or _text_
        # want Discord to render them as italic (IRC uses control codes for formatting).
        assert irc_to_discord("a*b") == "a*b"
        assert irc_to_discord("a_b") == "a_b"
        assert irc_to_discord("a`b") == "a\\`b"
        assert irc_to_discord("a~b") == "a\\~b"
        assert irc_to_discord("a|b") == "a\\|b"

    def test_literal_asterisk_italic_passthrough(self):
        # Real bug: *single set of astricks from irc* should render as italic on Discord
        assert irc_to_discord("*single set of astricks from irc*") == "*single set of astricks from irc*"
        assert irc_to_discord("**bold from irc**") == "**bold from irc**"

    def test_unclosed_bold(self):
        assert irc_to_discord(f"{_B}bold no close") == "**bold no close**"

    def test_unclosed_italic(self):
        assert irc_to_discord(f"{_I}italic no close") == "*italic no close*"

    def test_combined_bold_italic_underline(self):
        out = irc_to_discord(f"{_B}bold{_I}italic{_U}under{_R}")
        assert "**" in out
        assert "*" in out
        assert "__" in out


# ---------------------------------------------------------------------------
# irc_to_xmpp
# ---------------------------------------------------------------------------


class TestIrcToXmpp:
    """Test IRC control codes → XEP-0393 Message Styling."""

    def test_bold(self):
        assert irc_to_xmpp("\x02bold\x02") == "*bold*"

    def test_italic(self):
        assert irc_to_xmpp("\x1ditalic\x1d") == "_italic_"

    def test_strikethrough(self):
        assert irc_to_xmpp("\x1estrike\x1e") == "~strike~"

    def test_monospace(self):
        assert irc_to_xmpp("\x11mono\x11") == "`mono`"

    def test_underline_stripped(self):
        # No XEP-0393 equivalent
        assert irc_to_xmpp("\x1funder\x1f") == "under"

    def test_reverse_stripped(self):
        assert irc_to_xmpp("\x16text\x16") == "text"

    def test_color_stripped(self):
        assert irc_to_xmpp("\x0312colored\x03") == "colored"

    def test_rgb_color_stripped(self):
        assert irc_to_xmpp("\x04ff0000red\x0f") == "red"

    def test_reset_closes_bold(self):
        assert irc_to_xmpp("\x02bold\x0fafter") == "*bold*after"

    def test_reset_closes_mono(self):
        assert irc_to_xmpp("\x11mono\x0fafter") == "`mono`after"

    def test_unclosed_bold(self):
        assert irc_to_xmpp("\x02no close") == "*no close*"

    def test_unclosed_mono(self):
        assert irc_to_xmpp("\x11no close") == "`no close`"

    def test_mixed(self):
        assert irc_to_xmpp("\x02bold\x02 and \x1ditalic\x1d") == "*bold* and _italic_"

    def test_plain_passthrough(self):
        assert irc_to_xmpp("plain text") == "plain text"

    def test_empty(self):
        assert irc_to_xmpp("") == ""

    def test_mono_content_not_converted(self):
        # Bold codes inside monospace should pass through literally
        assert irc_to_xmpp("\x11\x02not bold\x02\x11") == "`\x02not bold\x02`"


# ---------------------------------------------------------------------------
# split_irc_message
# ---------------------------------------------------------------------------


class TestSplitIrcMessage:
    """Test IRC message splitting at byte boundaries."""

    def test_short_content_unchanged(self):
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
        content = "日本語" * 50
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
        content = "a" * 49 + "é"
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


# ---------------------------------------------------------------------------
# CTCP ACTION relay formatting
# ---------------------------------------------------------------------------


class TestCtcpActionFormatting:
    """Test /me action formatting through the relay transform layer."""

    def test_irc_action_content_to_discord_wrapped_italic(self):
        """IRC CTCP ACTION content arrives as plain text; relay wraps in _italics_ for Discord."""
        # The relay does: if evt.is_action and target == "discord": content = f"_{content}_"
        # irc_to_discord converts IRC codes in the content first, then relay wraps
        content = irc_to_discord("dances around")
        wrapped = f"_{content}_"
        assert wrapped == "_dances around_"

    def test_irc_action_with_formatting_to_discord(self):
        """IRC action with bold codes: codes converted, then wrapped in italics."""
        content = irc_to_discord("\x02boldly\x02 dances")
        wrapped = f"_{content}_"
        assert wrapped == "_**boldly** dances_"

    def test_discord_action_content_to_irc_plain(self):
        """Discord /me content (after stripping /me prefix) converts to IRC plain text."""
        # Discord adapter strips '/me ' prefix; relay calls discord_to_irc on the remainder
        action_text = "waves hello"
        irc_content = discord_to_irc(action_text)
        assert irc_content == "waves hello"

    def test_discord_action_with_markdown_to_irc(self):
        """Discord /me with markdown: markdown converted to IRC codes."""
        action_text = "**boldly** waves"
        irc_content = discord_to_irc(action_text)
        assert irc_content == f"{_B}boldly{_B} waves"

    def test_irc_ctcp_action_format(self):
        """CTCP ACTION wire format: content wrapped in \\x01ACTION ...\\x01."""
        chunk = "dances around"
        ctcp = f"\x01ACTION {chunk}\x01"
        assert ctcp.startswith("\x01ACTION ")
        assert ctcp.endswith("\x01")
        assert "dances around" in ctcp
