"""Adversarial tests for message overflow and boundary conditions.

Tests IRC 512-byte limit, message splitting with large payloads,
empty messages, whitespace-only messages, and formatting-only messages.

Validates: Requirement 15.4
"""

from __future__ import annotations

import pytest
from bridge.formatting.converter import convert
from bridge.formatting.splitter import split_irc_message
from bridge.gateway.pipeline import Pipeline, TransformContext
from bridge.gateway.steps import format_convert

# ---------------------------------------------------------------------------
# IRC 512-byte limit
# ---------------------------------------------------------------------------


class TestIRC512ByteLimit:
    """Messages at and around the IRC 512-byte limit."""

    def test_message_at_512_bytes(self) -> None:
        """A message exactly at 512 bytes should produce a single chunk."""
        text = "a" * 512
        chunks = split_irc_message(text, max_bytes=512)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_message_exceeding_512_bytes(self) -> None:
        """A message exceeding 512 bytes should be split correctly."""
        text = "a" * 1024
        chunks = split_irc_message(text, max_bytes=512)
        assert len(chunks) == 2
        assert "".join(chunks) == text
        for chunk in chunks:
            assert len(chunk.encode("utf-8")) <= 512

    def test_message_at_default_450_limit(self) -> None:
        """Default max_bytes=450 leaves room for IRC protocol overhead."""
        text = "b" * 900
        chunks = split_irc_message(text)
        assert len(chunks) == 2
        assert "".join(chunks) == text
        for chunk in chunks:
            assert len(chunk.encode("utf-8")) <= 450

    def test_multibyte_at_boundary(self) -> None:
        """Multi-byte characters at the split boundary must not be broken."""
        # Each emoji is 4 bytes in UTF-8
        text = "🔥" * 128  # 512 bytes total
        chunks = split_irc_message(text, max_bytes=512)
        assert "".join(chunks) == text
        for chunk in chunks:
            assert len(chunk.encode("utf-8")) <= 512
            # Each chunk must be valid UTF-8 (no broken surrogates)
            chunk.encode("utf-8")

    def test_3byte_chars_at_boundary(self) -> None:
        """3-byte UTF-8 characters at the split boundary."""
        # CJK character: 3 bytes each
        text = "中" * 200  # 600 bytes
        chunks = split_irc_message(text, max_bytes=512)
        assert "".join(chunks) == text
        for chunk in chunks:
            assert len(chunk.encode("utf-8")) <= 512


# ---------------------------------------------------------------------------
# Very large messages
# ---------------------------------------------------------------------------


class TestHugePayloads:
    """Messages with very large payloads (100KB+)."""

    def test_100kb_ascii_message(self) -> None:
        """100KB ASCII message should split without error."""
        text = "x" * 100_000
        chunks = split_irc_message(text, max_bytes=450)
        assert "".join(chunks) == text
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.encode("utf-8")) <= 450

    def test_100kb_unicode_message(self) -> None:
        """100KB of multi-byte Unicode should split correctly."""
        # ~33K emoji, each 4 bytes = ~132KB
        text = "🎉" * 33_000
        chunks = split_irc_message(text, max_bytes=450)
        assert "".join(chunks) == text
        for chunk in chunks:
            assert len(chunk.encode("utf-8")) <= 450

    def test_large_message_through_pipeline(self) -> None:
        """A large message should survive pipeline transformation."""
        text = "hello world " * 5000  # ~60KB
        ctx = TransformContext(origin="discord", target="irc")
        pipeline = Pipeline([format_convert])
        result = pipeline.transform(text, ctx)
        assert result is not None
        assert len(result) > 0

    def test_large_message_conversion(self) -> None:
        """Large message through format conversion should not crash."""
        text = "test message " * 8000  # ~104KB
        result = convert(text, "discord", "xmpp")
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Whitespace-only messages
# ---------------------------------------------------------------------------


class TestWhitespaceMessages:
    """Messages containing only whitespace."""

    @pytest.mark.parametrize(
        "text",
        [
            " ",
            "   ",
            "\t",
            "\n",
            "\r\n",
            " \t \n ",
        ],
        ids=["single-space", "multi-space", "tab", "newline", "crlf", "mixed"],
    )
    def test_whitespace_only_conversion(self, text: str) -> None:
        """Whitespace-only messages should not crash conversion."""
        for origin, target in [("discord", "irc"), ("irc", "xmpp"), ("xmpp", "discord")]:
            result = convert(text, origin, target)
            assert isinstance(result, str)

    @pytest.mark.parametrize(
        "text",
        [" ", "\t\t", "\n\n\n"],
    )
    def test_whitespace_only_splitting(self, text: str) -> None:
        """Whitespace-only messages should split without error."""
        chunks = split_irc_message(text, max_bytes=450)
        assert "".join(chunks) == text


# ---------------------------------------------------------------------------
# Empty messages
# ---------------------------------------------------------------------------


class TestEmptyMessages:
    """Empty string messages."""

    def test_empty_conversion(self) -> None:
        """Empty string should convert without error."""
        for origin, target in [("discord", "irc"), ("irc", "xmpp"), ("xmpp", "discord")]:
            result = convert("", origin, target)
            assert result == ""

    def test_empty_splitting(self) -> None:
        """Empty string should produce no chunks."""
        chunks = split_irc_message("", max_bytes=450)
        assert chunks == []

    def test_empty_through_pipeline(self) -> None:
        """Empty string through pipeline should not crash."""
        ctx = TransformContext(origin="discord", target="irc")
        pipeline = Pipeline([format_convert])
        result = pipeline.transform("", ctx)
        assert result == ""


# ---------------------------------------------------------------------------
# Formatting-only messages
# ---------------------------------------------------------------------------


class TestFormattingOnlyMessages:
    """Messages containing only formatting markers with no visible text."""

    def test_discord_formatting_only(self) -> None:
        """Discord formatting markers with no content."""
        for text in ["****", "____", "~~~~", "``", "||  ||"]:
            result = convert(text, "discord", "irc")
            assert isinstance(result, str)

    def test_irc_formatting_only(self) -> None:
        """IRC control codes with no visible text."""
        # Bold on, bold off
        text = "\x02\x02"
        result = convert(text, "irc", "discord")
        assert isinstance(result, str)

    def test_irc_reset_only(self) -> None:
        """Just a reset code."""
        text = "\x0f"
        result = convert(text, "irc", "discord")
        assert isinstance(result, str)

    def test_irc_color_only(self) -> None:
        """Just color codes with no text."""
        text = "\x0304,04\x03"
        result = convert(text, "irc", "discord")
        assert isinstance(result, str)
