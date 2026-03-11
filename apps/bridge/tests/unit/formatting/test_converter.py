"""Unit tests for bridge.formatting.converter — registry-based format conversion."""

from __future__ import annotations

import pytest
from bridge.formatting.converter import ProtocolName, convert, strip_formatting

# ---------------------------------------------------------------------------
# Same-protocol identity (Requirement 1.2)
# ---------------------------------------------------------------------------


class TestSameProtocolIdentity:
    """convert(content, p, p) must return content unchanged."""

    @pytest.mark.parametrize("protocol", ["discord", "irc", "xmpp"])
    def test_plain_text_unchanged(self, protocol: ProtocolName) -> None:
        text = "hello world"
        assert convert(text, protocol, protocol) == text

    @pytest.mark.parametrize("protocol", ["discord", "irc", "xmpp"])
    def test_empty_string_unchanged(self, protocol: ProtocolName) -> None:
        assert convert("", protocol, protocol) == ""

    @pytest.mark.parametrize("protocol", ["discord", "irc", "xmpp"])
    def test_formatted_text_unchanged(self, protocol: ProtocolName) -> None:
        # Even formatted text should be returned as-is for same protocol
        text = "**bold** and *italic*"
        assert convert(text, protocol, protocol) == text


# ---------------------------------------------------------------------------
# Cross-protocol conversion (Requirement 1.1)
# ---------------------------------------------------------------------------


class TestCrossProtocolConversion:
    """convert(content, origin, target) parses via origin and emits via target."""

    def test_discord_to_irc_bold(self) -> None:
        result = convert("**hello**", "discord", "irc")
        # IRC bold is \x02text\x02
        assert "\x02" in result
        assert "hello" in result

    def test_irc_to_discord_bold(self) -> None:
        result = convert("\x02hello\x02", "irc", "discord")
        assert "**hello**" in result

    def test_discord_to_xmpp_bold(self) -> None:
        result = convert("**hello**", "discord", "xmpp")
        # XEP-0393 bold is *hello*
        assert "hello" in result

    def test_discord_to_irc_inline_code(self) -> None:
        """Discord `code` → IRC emits \\x11 (MONOSPACE) for HexChat/ObsidianIRC."""
        result = convert("hello `world` end", "discord", "irc")
        assert "\x11" in result
        assert "world" in result

    def test_xmpp_to_irc_inline_code(self) -> None:
        """XMPP `code` → IRC emits \\x11 (MONOSPACE)."""
        result = convert("hello `world` end", "xmpp", "irc")
        assert "\x11" in result
        assert "world" in result

    def test_irc_to_discord_inline_code(self) -> None:
        """IRC \\x11 (MONOSPACE) → Discord emits `code`."""
        result = convert("hello \x11world\x11 end", "irc", "discord")
        assert "`world`" in result

    def test_plain_text_survives_conversion(self) -> None:
        """Plain text without formatting markers should survive any conversion."""
        text = "just plain text"
        for origin in ("discord", "irc", "xmpp"):
            for target in ("discord", "irc", "xmpp"):
                result = convert(text, origin, target)
                assert strip_formatting(result, target) == text


# ---------------------------------------------------------------------------
# strip_formatting helper
# ---------------------------------------------------------------------------


class TestStripFormatting:
    """strip_formatting should return plain text with markers removed."""

    def test_discord_bold(self) -> None:
        assert strip_formatting("**bold**", "discord") == "bold"

    def test_irc_bold(self) -> None:
        assert strip_formatting("\x02bold\x02", "irc") == "bold"

    def test_xmpp_bold(self) -> None:
        assert strip_formatting("*bold*", "xmpp") == "bold"

    def test_plain_text(self) -> None:
        assert strip_formatting("hello", "discord") == "hello"

    def test_empty_string(self) -> None:
        assert strip_formatting("", "discord") == ""


# ---------------------------------------------------------------------------
# Registry coverage
# ---------------------------------------------------------------------------


class TestRegistryCoverage:
    """All three protocols must be present in both registries."""

    def test_all_protocol_pairs_work(self) -> None:
        protocols: list[ProtocolName] = ["discord", "irc", "xmpp"]
        for origin in protocols:
            for target in protocols:
                # Should not raise KeyError
                convert("test", origin, target)
