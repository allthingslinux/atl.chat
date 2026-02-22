"""Edge-case tests for irc_message_split: UTF-8 boundary handling."""

from __future__ import annotations

from bridge.formatting.irc_message_split import split_irc_message


class TestSplitIrcMessageUtf8:
    def test_empty_content_returns_empty_list(self):
        assert split_irc_message("") == []

    def test_short_ascii_is_single_chunk(self):
        assert split_irc_message("hello", max_bytes=50) == ["hello"]

    def test_exact_byte_boundary_is_single_chunk(self):
        content = "a" * 450
        assert split_irc_message(content, max_bytes=450) == [content]

    def test_long_content_produces_multiple_chunks(self):
        content = "word " * 200  # 1000 bytes
        chunks = split_irc_message(content, max_bytes=100)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.encode("utf-8")) <= 100

    def test_multi_byte_unicode_not_split_mid_codepoint(self):
        """Emoji (4 bytes each) must never be split across chunks."""
        content = "🎉" * 120  # 480 bytes
        chunks = split_irc_message(content, max_bytes=20)
        for chunk in chunks:
            chunk.encode("utf-8")  # validates no partial codepoints
        assert "".join(chunks) == content

    def test_cjk_characters_not_split_mid_codepoint(self):
        """3-byte CJK chars must stay intact."""
        content = "中文测试" * 50  # 600 bytes
        chunks = split_irc_message(content, max_bytes=50)
        for chunk in chunks:
            chunk.encode("utf-8")
        assert "".join(chunks) == content

    def test_mixed_ascii_and_unicode_splits_correctly(self):
        content = "Hello 😀 World 😀 " * 30
        chunks = split_irc_message(content, max_bytes=100)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.encode("utf-8")) <= 100
            chunk.encode("utf-8")

    def test_no_natural_word_boundary_falls_back_to_byte_boundary(self):
        """When there's no space in a huge word, split at byte limit."""
        long_word = "x" * 600
        chunks = split_irc_message(long_word, max_bytes=100)
        assert len(chunks) == 6
        for chunk in chunks:
            assert len(chunk.encode("utf-8")) <= 100

    def test_replace_invalid_bytes_decoded_content(self):
        """Content with replacement chars (from bad decode) doesn't crash."""
        raw = b"valid " + bytes([0xFF, 0xFE]) + b" more"
        content = raw.decode("utf-8", errors="replace")
        chunks = split_irc_message(content, max_bytes=50)
        assert "".join(chunks)  # non-empty round-trip

    def test_tiny_max_bytes_splits_single_emoji(self):
        """With max_bytes=4 each emoji (4 bytes) gets its own chunk."""
        content = "🎉🎊🎈"
        chunks = split_irc_message(content, max_bytes=4)
        assert len(chunks) == 3
        assert "".join(chunks) == content

    def test_two_byte_chars_land_at_valid_boundaries(self):
        """2-byte 'é' chars must not be split mid-sequence."""
        content = "é" * 200  # each é = 2 bytes
        chunks = split_irc_message(content, max_bytes=10)
        for chunk in chunks:
            chunk.encode("utf-8")
            # Each chunk must have even byte count since é = 2 bytes
            assert len(chunk.encode("utf-8")) % 2 == 0

    def test_prefers_word_boundary_over_mid_word(self):
        """Split should land at the last space when it's in the second half."""
        first = "a" * 60
        second = "b" * 40
        content = first + " " + second  # 101 bytes
        chunks = split_irc_message(content, max_bytes=100)
        # Split should separate first and second words
        assert chunks[0].rstrip() == first
        assert second in "".join(chunks)
