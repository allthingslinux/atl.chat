"""Unit tests for invalid XML 1.0 character stripping.

Tests cover:
- The low-level ``strip_invalid_xml_chars`` utility in ``formatting.primitives``
- The ``strip_invalid_xml`` pipeline step in ``gateway.steps``
"""

from __future__ import annotations

from bridge.formatting.primitives import strip_invalid_xml_chars
from bridge.gateway.pipeline import TransformContext
from bridge.gateway.steps import strip_invalid_xml

# ── strip_invalid_xml_chars utility ──────────────────────────────────────


class TestStripInvalidXmlChars:
    """Unit tests for the low-level stripping utility."""

    def test_tab_preserved(self) -> None:
        assert strip_invalid_xml_chars("a\tb") == "a\tb"

    def test_cr_preserved(self) -> None:
        assert strip_invalid_xml_chars("a\rb") == "a\rb"

    def test_lf_preserved(self) -> None:
        assert strip_invalid_xml_chars("a\nb") == "a\nb"

    def test_null_byte_stripped(self) -> None:
        assert strip_invalid_xml_chars("a\x00b") == "ab"

    def test_c0_controls_before_tab_stripped(self) -> None:
        # 0x01 through 0x08
        for code in range(0x01, 0x09):
            text = f"a{chr(code)}b"
            assert strip_invalid_xml_chars(text) == "ab", f"0x{code:02x} not stripped"

    def test_vertical_tab_stripped(self) -> None:
        assert strip_invalid_xml_chars("a\x0bb") == "ab"

    def test_form_feed_stripped(self) -> None:
        assert strip_invalid_xml_chars("a\x0cb") == "ab"

    def test_c0_controls_after_cr_stripped(self) -> None:
        # 0x0E through 0x1F
        for code in range(0x0E, 0x20):
            text = f"a{chr(code)}b"
            assert strip_invalid_xml_chars(text) == "ab", f"0x{code:02x} not stripped"

    def test_fffe_stripped(self) -> None:
        assert strip_invalid_xml_chars("a\ufffeb") == "ab"

    def test_ffff_stripped(self) -> None:
        assert strip_invalid_xml_chars("a\uffffb") == "ab"

    def test_normal_text_unchanged(self) -> None:
        text = "Hello, world! 🌍 café"
        assert strip_invalid_xml_chars(text) == text

    def test_empty_string(self) -> None:
        assert strip_invalid_xml_chars("") == ""

    def test_mixed_valid_and_invalid(self) -> None:
        # Tab and LF kept, null and BEL stripped
        text = "hello\t\x00world\n\x07!"
        assert strip_invalid_xml_chars(text) == "hello\tworld\n!"


# ── strip_invalid_xml pipeline step ──────────────────────────────────────


class TestStripInvalidXmlStep:
    """Unit tests for the pipeline step wrapper."""

    def test_applies_when_target_is_xmpp(self) -> None:
        ctx = TransformContext(origin="discord", target="xmpp")
        assert strip_invalid_xml("a\x00b", ctx) == "ab"

    def test_noop_when_target_is_discord(self) -> None:
        ctx = TransformContext(origin="irc", target="discord")
        assert strip_invalid_xml("a\x00b", ctx) == "a\x00b"

    def test_noop_when_target_is_irc(self) -> None:
        ctx = TransformContext(origin="discord", target="irc")
        assert strip_invalid_xml("a\x00b", ctx) == "a\x00b"

    def test_preserves_valid_content_for_xmpp(self) -> None:
        ctx = TransformContext(origin="irc", target="xmpp")
        assert strip_invalid_xml("hello world", ctx) == "hello world"

    def test_strips_fffe_for_xmpp(self) -> None:
        ctx = TransformContext(origin="discord", target="xmpp")
        assert strip_invalid_xml("a\ufffeb", ctx) == "ab"
