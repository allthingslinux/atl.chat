"""Unit tests for gateway.steps — pipeline step implementations."""

from __future__ import annotations

import re

from bridge.formatting.irc_codes import COLOR, RESET
from bridge.gateway.pipeline import TransformContext
from bridge.gateway.steps import (
    add_reply_fallback,
    format_convert,
    make_content_filter,
    strip_reply_fallback,
    unwrap_spoiler,
    wrap_spoiler,
)

# ── strip_reply_fallback ─────────────────────────────────────────────────


class TestStripReplyFallback:
    """strip_reply_fallback removes reply fallback lines."""

    def test_noop_without_reply_to_id(self) -> None:
        ctx = TransformContext(origin="xmpp", target="discord")
        assert strip_reply_fallback("> quoted\nactual", ctx) == "> quoted\nactual"

    def test_xmpp_strips_leading_quote_lines(self) -> None:
        ctx = TransformContext(origin="xmpp", target="discord", reply_to_id="msg-1")
        result = strip_reply_fallback("> old message\nmy reply", ctx)
        assert result == "my reply"

    def test_xmpp_strips_multiple_quote_lines(self) -> None:
        ctx = TransformContext(origin="xmpp", target="discord", reply_to_id="msg-1")
        result = strip_reply_fallback("> line1\n> line2\nmy reply", ctx)
        assert result == "my reply"

    def test_xmpp_returns_content_if_all_quoted(self) -> None:
        ctx = TransformContext(origin="xmpp", target="discord", reply_to_id="msg-1")
        result = strip_reply_fallback("> only quoted", ctx)
        # Should return original content when stripping would leave nothing
        assert result == "> only quoted"

    def test_irc_strips_leading_nick_line(self) -> None:
        ctx = TransformContext(origin="irc", target="discord", reply_to_id="msg-1")
        result = strip_reply_fallback("<alice> original msg\nmy reply", ctx)
        assert result == "my reply"

    def test_irc_noop_without_nick_prefix(self) -> None:
        ctx = TransformContext(origin="irc", target="discord", reply_to_id="msg-1")
        result = strip_reply_fallback("just a message", ctx)
        assert result == "just a message"

    def test_discord_origin_passthrough(self) -> None:
        ctx = TransformContext(origin="discord", target="irc", reply_to_id="msg-1")
        result = strip_reply_fallback("some content", ctx)
        assert result == "some content"


# ── unwrap_spoiler ────────────────────────────────────────────────────────


class TestUnwrapSpoiler:
    """unwrap_spoiler extracts spoiler markers and sets ctx.spoiler."""

    def test_discord_strips_spoiler_markers(self) -> None:
        ctx = TransformContext(origin="discord", target="irc")
        result = unwrap_spoiler("check ||secret|| out", ctx)
        assert result == "check secret out"
        assert ctx.spoiler is True

    def test_discord_no_spoiler(self) -> None:
        ctx = TransformContext(origin="discord", target="irc")
        result = unwrap_spoiler("normal message", ctx)
        assert result == "normal message"
        assert ctx.spoiler is False

    def test_discord_multiple_spoilers(self) -> None:
        ctx = TransformContext(origin="discord", target="irc")
        result = unwrap_spoiler("||a|| and ||b||", ctx)
        assert result == "a and b"
        assert ctx.spoiler is True

    def test_irc_detects_fg_eq_bg(self) -> None:
        ctx = TransformContext(origin="irc", target="discord")
        # fg=1, bg=1 → spoiler
        content = f"{COLOR}01,01hidden{RESET}"
        result = unwrap_spoiler(content, ctx)
        assert ctx.spoiler is True
        # Content is returned as-is (format_convert handles stripping)
        assert result == content

    def test_irc_no_spoiler(self) -> None:
        ctx = TransformContext(origin="irc", target="discord")
        unwrap_spoiler("plain text", ctx)
        assert ctx.spoiler is False

    def test_xmpp_spoiler_from_raw(self) -> None:
        ctx = TransformContext(
            origin="xmpp",
            target="discord",
            raw={"spoiler": True, "spoiler_reason": "plot twist"},
        )
        result = unwrap_spoiler("the ending is...", ctx)
        assert result == "the ending is..."
        assert ctx.spoiler is True
        assert ctx.spoiler_reason == "plot twist"

    def test_xmpp_xep_0382_key(self) -> None:
        ctx = TransformContext(origin="xmpp", target="discord", raw={"xep_0382": True})
        unwrap_spoiler("hidden", ctx)
        assert ctx.spoiler is True

    def test_xmpp_no_spoiler(self) -> None:
        ctx = TransformContext(origin="xmpp", target="discord")
        unwrap_spoiler("normal", ctx)
        assert ctx.spoiler is False


# ── format_convert ────────────────────────────────────────────────────────


class TestFormatConvert:
    """format_convert delegates to formatting.converter.convert."""

    def test_same_protocol_passthrough(self) -> None:
        ctx = TransformContext(origin="discord", target="discord")
        assert format_convert("**bold**", ctx) == "**bold**"

    def test_discord_to_irc(self) -> None:
        ctx = TransformContext(origin="discord", target="irc")
        result = format_convert("**bold**", ctx)
        assert "\x02" in result  # IRC bold control code

    def test_discord_to_xmpp_passthrough(self) -> None:
        """Discord→XMPP passes through raw content; XMPP adapter runs discord_to_xmpp."""
        ctx = TransformContext(origin="discord", target="xmpp")
        result = format_convert("**bold** and *italic*", ctx)
        assert result == "**bold** and *italic*"

    def test_plain_text_preserved(self) -> None:
        ctx = TransformContext(origin="irc", target="xmpp")
        assert format_convert("hello world", ctx) == "hello world"


# ── wrap_spoiler ──────────────────────────────────────────────────────────


class TestWrapSpoiler:
    """wrap_spoiler applies target-protocol spoiler markers."""

    def test_noop_when_no_spoiler(self) -> None:
        ctx = TransformContext(origin="irc", target="discord")
        assert wrap_spoiler("text", ctx) == "text"

    def test_discord_target(self) -> None:
        ctx = TransformContext(origin="irc", target="discord", spoiler=True)
        assert wrap_spoiler("secret", ctx) == "||secret||"

    def test_irc_target(self) -> None:
        ctx = TransformContext(origin="discord", target="irc", spoiler=True)
        result = wrap_spoiler("secret", ctx)
        assert result.startswith(COLOR)
        assert result.endswith(RESET)
        assert "secret" in result

    def test_xmpp_target_sets_raw(self) -> None:
        ctx = TransformContext(origin="discord", target="xmpp", spoiler=True)
        result = wrap_spoiler("secret", ctx)
        assert result == "secret"  # content unchanged
        assert ctx.raw["spoiler"] is True

    def test_xmpp_target_with_reason(self) -> None:
        ctx = TransformContext(
            origin="discord",
            target="xmpp",
            spoiler=True,
            spoiler_reason="plot twist",
        )
        wrap_spoiler("secret", ctx)
        assert ctx.raw["spoiler_reason"] == "plot twist"


# ── add_reply_fallback ────────────────────────────────────────────────────


class TestAddReplyFallback:
    """add_reply_fallback prepends reply indicator for IRC targets."""

    def test_irc_target_with_reply_no_quoted(self) -> None:
        """Without reply_quoted_content, content passes through unchanged."""
        ctx = TransformContext(origin="discord", target="irc", reply_to_id="msg-1")
        assert add_reply_fallback("my reply", ctx) == "my reply"

    def test_irc_target_with_reply_and_quoted(self) -> None:
        """With reply_quoted_content, format as > quoted | reply."""
        ctx = TransformContext(
            origin="discord",
            target="irc",
            reply_to_id="msg-1",
            raw={"reply_quoted_content": "original message"},
        )
        assert add_reply_fallback("my reply", ctx) == "> original message | my reply"
        assert ctx.raw.get("reply_fallback_added") is True

    def test_irc_target_with_reply_and_author(self) -> None:
        """With reply_quoted_author, prepend author: prefix."""
        ctx = TransformContext(
            origin="discord",
            target="irc",
            reply_to_id="msg-1",
            raw={"reply_quoted_content": "hi", "reply_quoted_author": "kaizen"},
        )
        assert add_reply_fallback("ok", ctx) == "kaizen: > hi | ok"

    def test_irc_target_no_reply(self) -> None:
        ctx = TransformContext(origin="discord", target="irc")
        assert add_reply_fallback("no reply", ctx) == "no reply"

    def test_non_irc_target_passthrough(self) -> None:
        ctx = TransformContext(origin="irc", target="discord", reply_to_id="msg-1")
        assert add_reply_fallback("my reply", ctx) == "my reply"


# ── content_filter ────────────────────────────────────────────────────────


class TestContentFilter:
    """make_content_filter returns a step that drops matching content."""

    def test_drops_matching_content(self) -> None:
        step = make_content_filter([re.compile(r"spam")])
        ctx = TransformContext(origin="discord", target="irc")
        assert step("this is spam", ctx) is None

    def test_passes_non_matching_content(self) -> None:
        step = make_content_filter([re.compile(r"spam")])
        ctx = TransformContext(origin="discord", target="irc")
        assert step("hello world", ctx) == "hello world"

    def test_empty_content_never_filtered(self) -> None:
        step = make_content_filter([re.compile(r".*")])
        ctx = TransformContext(origin="discord", target="irc")
        assert step("", ctx) == ""

    def test_multiple_patterns(self) -> None:
        step = make_content_filter([re.compile(r"spam"), re.compile(r"ads")])
        ctx = TransformContext(origin="discord", target="irc")
        assert step("buy ads now", ctx) is None
        assert step("clean message", ctx) == "clean message"

    def test_no_patterns_passes_everything(self) -> None:
        step = make_content_filter([])
        ctx = TransformContext(origin="discord", target="irc")
        assert step("anything", ctx) == "anything"
