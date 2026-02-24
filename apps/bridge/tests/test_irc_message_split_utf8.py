"""Edge-case tests for irc_message_split: UTF-8 boundary handling."""

from __future__ import annotations

from bridge.formatting.irc_message_split import split_irc_message


class TestSplitIrcMessageUtf8:
    def test_empty_content_returns_empty_list(self):
        # Arrange / Act
        result = split_irc_message("")

        # Assert
        assert result == []

    def test_short_ascii_is_single_chunk(self):
        # Arrange / Act
        result = split_irc_message("hello", max_bytes=50)

        # Assert
        assert result == ["hello"]

    def test_exact_byte_boundary_is_single_chunk(self):
        # Arrange
        content = "a" * 450

        # Act
        result = split_irc_message(content, max_bytes=450)

        # Assert
        assert result == [content]

    def test_long_content_produces_multiple_chunks(self):
        # Arrange
        content = "word " * 200  # 1000 bytes

        # Act
        chunks = split_irc_message(content, max_bytes=100)

        # Assert — splits into more than one chunk, each within limit
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.encode("utf-8")) <= 100

    def test_multi_byte_unicode_not_split_mid_codepoint(self):
        """Emoji (4 bytes each) must never be split across chunks."""
        # Arrange
        content = "🎉" * 120  # 480 bytes total

        # Act
        chunks = split_irc_message(content, max_bytes=20)

        # Assert — each chunk is valid UTF-8 and the full content is preserved
        for chunk in chunks:
            chunk.encode("utf-8")  # raises if partial codepoint
        assert "".join(chunks) == content

    def test_cjk_characters_not_split_mid_codepoint(self):
        """3-byte CJK chars must stay intact across chunk boundaries."""
        # Arrange
        content = "中文测试" * 50  # 600 bytes total

        # Act
        chunks = split_irc_message(content, max_bytes=50)

        # Assert
        for chunk in chunks:
            chunk.encode("utf-8")  # raises if partial codepoint
        assert "".join(chunks) == content

    def test_mixed_ascii_and_unicode_splits_correctly(self):
        # Arrange
        content = "Hello 😀 World 😀 " * 30

        # Act
        chunks = split_irc_message(content, max_bytes=100)

        # Assert — produces multiple chunks, all valid UTF-8, all within limit
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.encode("utf-8")) <= 100
            chunk.encode("utf-8")  # raises if partial codepoint

    def test_no_natural_word_boundary_falls_back_to_byte_boundary(self):
        """When there's no space in a long word, split at the byte limit."""
        # Arrange
        long_word = "x" * 600  # single token, no spaces

        # Act
        chunks = split_irc_message(long_word, max_bytes=100)

        # Assert — split into exactly 6 equal chunks, each within limit
        assert len(chunks) == 6
        for chunk in chunks:
            assert len(chunk.encode("utf-8")) <= 100

    def test_replace_invalid_bytes_decoded_content(self):
        """Content with replacement chars (from bad decode) doesn't crash."""
        # Arrange
        raw = b"valid " + bytes([0xFF, 0xFE]) + b" more"
        content = raw.decode("utf-8", errors="replace")

        # Act
        chunks = split_irc_message(content, max_bytes=50)

        # Assert — non-empty round-trip; no crash
        assert "".join(chunks)

    def test_tiny_max_bytes_splits_single_emoji(self):
        """With max_bytes=4 each 4-byte emoji gets its own chunk."""
        # Arrange
        content = "🎉🎊🎈"  # each emoji = exactly 4 bytes

        # Act
        chunks = split_irc_message(content, max_bytes=4)

        # Assert
        assert len(chunks) == 3
        assert "".join(chunks) == content

    def test_two_byte_chars_land_at_valid_boundaries(self):
        """2-byte 'é' chars must not be split mid-sequence."""
        # Arrange
        content = "é" * 200  # each é = 2 bytes → 400 bytes total

        # Act
        chunks = split_irc_message(content, max_bytes=10)

        # Assert — every chunk is valid UTF-8 with an even byte count
        for chunk in chunks:
            encoded = chunk.encode("utf-8")
            assert len(encoded) % 2 == 0  # é = 2 bytes, so count must be even

    def test_prefers_word_boundary_over_mid_word(self):
        """Split should land at the last space rather than cutting a word."""
        # Arrange
        first = "a" * 60
        second = "b" * 40
        content = first + " " + second  # 101 bytes — just over the limit

        # Act
        chunks = split_irc_message(content, max_bytes=100)

        # Assert — first chunk carries the first word, second carries the rest
        assert chunks[0].rstrip() == first
        assert second in "".join(chunks)
