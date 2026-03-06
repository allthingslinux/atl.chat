"""Tests for IRC charset handling (Requirement 16.2).

Verifies UTF-8 → ISO-8859-1 fallback decoding.
"""

from __future__ import annotations

from bridge.adapters.irc.handlers import decode_irc_bytes


class TestDecodeIrcBytes:
    """Unit tests for the decode_irc_bytes utility."""

    def test_valid_utf8_decoded(self) -> None:
        data = b"Hello, world!"
        assert decode_irc_bytes(data) == "Hello, world!"

    def test_utf8_emoji_decoded(self) -> None:
        data = "Hello 🌍".encode()
        assert decode_irc_bytes(data) == "Hello 🌍"

    def test_invalid_utf8_falls_back_to_latin1(self) -> None:
        # ISO-8859-1 encoded string with accented characters
        data = "caf\xe9".encode("iso-8859-1")
        result = decode_irc_bytes(data)
        assert result == "café"

    def test_pure_ascii_decoded(self) -> None:
        data = b"plain ascii"
        assert decode_irc_bytes(data) == "plain ascii"

    def test_empty_bytes_decoded(self) -> None:
        assert decode_irc_bytes(b"") == ""

    def test_mixed_high_bytes_fall_back(self) -> None:
        # Bytes 0x80-0xFF that aren't valid UTF-8 sequences
        data = bytes([0xC0, 0xC1])  # Invalid UTF-8 lead bytes
        result = decode_irc_bytes(data)
        # Should decode as ISO-8859-1 without error
        assert len(result) == 2
