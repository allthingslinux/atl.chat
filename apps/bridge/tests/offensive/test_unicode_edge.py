"""Adversarial tests for Unicode edge cases in formatting conversion.

Tests zero-width spaces, RTL overrides, emoji sequences, surrogate pairs,
private-use area characters, combining characters, and long Unicode sequences.

Validates: Requirement 15.4
"""

from __future__ import annotations

import pytest
from bridge.formatting.converter import convert
from bridge.formatting.primitives import ZWS_RE, strip_invalid_xml_chars
from bridge.identity.sanitize import ensure_valid_username, sanitize_nick

# ---------------------------------------------------------------------------
# Zero-width spaces
# ---------------------------------------------------------------------------


class TestZeroWidthSpaces:
    """ZWS (U+200B) should be handled by ZWS_RE without crashing."""

    def test_zws_detected_by_regex(self) -> None:
        text = "hello\u200bworld"
        assert ZWS_RE.search(text) is not None

    def test_zws_in_conversion_does_not_crash(self) -> None:
        text = "hello\u200bworld"
        for origin in ("discord", "irc", "xmpp"):
            for target in ("discord", "irc", "xmpp"):
                result = convert(text, origin, target)
                assert isinstance(result, str)

    def test_zws_only_message(self) -> None:
        text = "\u200b\u200b\u200b"
        result = convert(text, "discord", "irc")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Right-to-left override characters
# ---------------------------------------------------------------------------


class TestRTLOverride:
    """RTL override (U+202E) and related bidi characters should not crash
    the formatting pipeline."""

    @pytest.mark.parametrize(
        "char,name",
        [
            ("\u202e", "RTL-override"),
            ("\u202d", "LTR-override"),
            ("\u200f", "RTL-mark"),
            ("\u200e", "LTR-mark"),
            ("\u2069", "pop-directional-isolate"),
            ("\u2066", "LTR-isolate"),
            ("\u2067", "RTL-isolate"),
        ],
    )
    def test_bidi_chars_in_conversion(self, char: str, name: str) -> None:
        text = f"hello{char}world"
        for origin, target in [("discord", "irc"), ("irc", "xmpp"), ("xmpp", "discord")]:
            result = convert(text, origin, target)
            assert isinstance(result, str)

    def test_rtl_override_in_nick_sanitization(self) -> None:
        """RTL override in a nick should not produce an invalid nick."""
        nick = "\u202eevil_nick"
        result = sanitize_nick(nick)
        assert len(result) > 0
        assert len(result) <= 23


# ---------------------------------------------------------------------------
# Emoji sequences
# ---------------------------------------------------------------------------


class TestEmojiSequences:
    """Multi-codepoint emoji should survive conversion without corruption."""

    @pytest.mark.parametrize(
        "emoji,name",
        [
            ("👨‍👩‍👧‍👦", "family-emoji"),
            ("🏳️‍🌈", "rainbow-flag"),
            ("👩🏽‍💻", "woman-technologist-medium-skin"),
            ("🇺🇸", "flag-us"),
            ("😀", "simple-emoji"),
            ("🧑‍🤝‍🧑", "people-holding-hands"),
        ],
    )
    def test_emoji_survives_conversion(self, emoji: str, name: str) -> None:
        text = f"hello {emoji} world"
        for origin, target in [("discord", "irc"), ("irc", "xmpp"), ("xmpp", "discord")]:
            result = convert(text, origin, target)
            assert emoji in result

    def test_emoji_in_username(self) -> None:
        name = "user 🎮 name"
        result = ensure_valid_username(name)
        assert 2 <= len(result) <= 32

    def test_emoji_only_message(self) -> None:
        text = "👍👎🔥"
        result = convert(text, "discord", "irc")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Surrogate pairs (should not crash)
# ---------------------------------------------------------------------------


class TestSurrogatePairs:
    """Surrogate-related edge cases should not crash the system."""

    def test_supplementary_plane_chars(self) -> None:
        """Characters from supplementary planes (U+10000+) should work."""
        # Musical symbol G clef (U+1D11E)
        text = "music: 𝄞 end"
        result = convert(text, "discord", "irc")
        assert "𝄞" in result

    def test_strip_invalid_xml_handles_supplementary(self) -> None:
        """Supplementary plane characters are valid XML and should be preserved."""
        text = "emoji: \U0001f600 math: \U0001d54f"
        result = strip_invalid_xml_chars(text)
        assert "\U0001f600" in result
        assert "\U0001d54f" in result


# ---------------------------------------------------------------------------
# Private-use area characters
# ---------------------------------------------------------------------------


class TestPrivateUseArea:
    """Private-use area characters (U+E000-U+F8FF) should not crash."""

    def test_pua_in_conversion(self) -> None:
        text = "before\ue000\uf8ffafter"
        result = convert(text, "discord", "irc")
        assert isinstance(result, str)

    def test_pua_in_nick(self) -> None:
        nick = "user\ue000name"
        result = sanitize_nick(nick)
        assert len(result) > 0
        assert len(result) <= 23


# ---------------------------------------------------------------------------
# Combining characters
# ---------------------------------------------------------------------------


class TestCombiningCharacters:
    """Combining characters (diacritics, etc.) should not crash or corrupt."""

    def test_combining_diacriticals(self) -> None:
        # "Zalgo" text: e + combining chars
        text = "h̷̢̧̛̗̣̱̝̦̲̤̙̪̫̬̭̮̯̰̱̲̳̹̺̻̼̀́̂̃̄̅̆̇̈̉̊̋̌̍̎̏̐̑̒̓̔̕̚ello"
        result = convert(text, "discord", "irc")
        assert isinstance(result, str)

    def test_combining_in_nick(self) -> None:
        nick = "ùser"  # u + combining grave
        result = sanitize_nick(nick)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Very long Unicode sequences
# ---------------------------------------------------------------------------


class TestLongUnicodeSequences:
    """Very long strings of Unicode should not cause excessive memory or time."""

    def test_long_emoji_sequence(self) -> None:
        text = "🔥" * 1000
        result = convert(text, "discord", "irc")
        assert len(result) >= 1000

    def test_long_combining_sequence(self) -> None:
        # Many combining characters on a single base
        text = "a" + "\u0300" * 500
        result = convert(text, "discord", "xmpp")
        assert isinstance(result, str)

    def test_long_zws_sequence(self) -> None:
        text = "\u200b" * 5000
        result = convert(text, "irc", "discord")
        assert isinstance(result, str)
