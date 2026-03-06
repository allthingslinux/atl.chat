"""Unit tests for formatting/splitter.py — IRC message splitting."""

from __future__ import annotations

from bridge.formatting.splitter import split_irc_message


class TestSplitIrcMessageBasic:
    """Core behaviour: empty input, short input, default max_bytes."""

    def test_empty_string_returns_empty_list(self):
        assert split_irc_message("") == []

    def test_short_ascii_single_chunk(self):
        assert split_irc_message("hello", max_bytes=50) == ["hello"]

    def test_exact_boundary_single_chunk(self):
        text = "a" * 450
        assert split_irc_message(text) == [text]

    def test_default_max_bytes_is_450(self):
        text = "a" * 451
        chunks = split_irc_message(text)
        assert len(chunks) == 2
        assert "".join(chunks) == text


class TestSplitIrcMessageConcatenation:
    """Concatenation of chunks must always equal the original text."""

    def test_ascii_concatenation(self):
        text = "word " * 200
        chunks = split_irc_message(text, max_bytes=100)
        assert "".join(chunks) == text

    def test_emoji_concatenation(self):
        text = "🎉" * 120
        chunks = split_irc_message(text, max_bytes=20)
        assert "".join(chunks) == text

    def test_cjk_concatenation(self):
        text = "中文测试" * 50
        chunks = split_irc_message(text, max_bytes=50)
        assert "".join(chunks) == text

    def test_mixed_content_concatenation(self):
        text = "Hello 😀 World 中文 " * 30
        chunks = split_irc_message(text, max_bytes=80)
        assert "".join(chunks) == text


class TestSplitIrcMessageByteLimits:
    """Every chunk must encode to at most max_bytes in UTF-8."""

    def test_ascii_chunks_within_limit(self):
        text = "x" * 600
        for chunk in split_irc_message(text, max_bytes=100):
            assert len(chunk.encode("utf-8")) <= 100

    def test_emoji_chunks_within_limit(self):
        text = "🎉🎊🎈" * 40
        for chunk in split_irc_message(text, max_bytes=20):
            assert len(chunk.encode("utf-8")) <= 20

    def test_two_byte_chars_within_limit(self):
        text = "é" * 200
        for chunk in split_irc_message(text, max_bytes=10):
            assert len(chunk.encode("utf-8")) <= 10

    def test_three_byte_chars_within_limit(self):
        text = "中" * 200
        for chunk in split_irc_message(text, max_bytes=10):
            assert len(chunk.encode("utf-8")) <= 10


class TestSplitIrcMessageUtf8Safety:
    """Multi-byte UTF-8 characters must never be split mid-codepoint."""

    def test_four_byte_emoji_not_split(self):
        text = "🎉" * 120
        for chunk in split_irc_message(text, max_bytes=5):
            chunk.encode("utf-8")  # raises on partial codepoint

    def test_three_byte_cjk_not_split(self):
        text = "中文" * 100
        for chunk in split_irc_message(text, max_bytes=7):
            chunk.encode("utf-8")

    def test_two_byte_accented_not_split(self):
        text = "é" * 200
        for chunk in split_irc_message(text, max_bytes=3):
            chunk.encode("utf-8")

    def test_single_emoji_per_chunk_at_exact_size(self):
        text = "🎉🎊🎈"
        chunks = split_irc_message(text, max_bytes=4)
        assert len(chunks) == 3
        assert "".join(chunks) == text


class TestSplitIrcMessageEdgeCases:
    """Edge cases: tiny limits, single characters, boundary alignment."""

    def test_max_bytes_equals_one_forces_ascii_chars(self):
        text = "abc"
        chunks = split_irc_message(text, max_bytes=1)
        assert chunks == ["a", "b", "c"]

    def test_single_multibyte_char_wider_than_limit(self):
        # 4-byte emoji with max_bytes=2: must still produce the character
        text = "🎉"
        chunks = split_irc_message(text, max_bytes=2)
        assert "".join(chunks) == text
        assert len(chunks) == 1  # can't split a single char

    def test_mixed_widths_at_boundary(self):
        # 'a' (1 byte) + '中' (3 bytes) = 4 bytes, limit=3
        text = "a中"
        chunks = split_irc_message(text, max_bytes=3)
        assert "".join(chunks) == text
        for chunk in chunks:
            # Each chunk is valid UTF-8
            chunk.encode("utf-8")
