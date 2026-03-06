"""Property-based tests for IRC message splitting (CP3).

**Validates: Requirements 5.1, 5.2, 5.3**

Property CP3: Message Splitting Completeness and Byte Safety
  For any input text and configured max_bytes, concatenating all chunks
  produced by ``split_irc_message`` equals the original text, and every
  chunk encodes to at most max_bytes in UTF-8.
"""

from __future__ import annotations

from bridge.formatting.splitter import split_irc_message
from hypothesis import given, settings
from hypothesis import strategies as st


class TestSplitPreservesAllContent:
    """Concatenation of all chunks must equal the original text.

    **Validates: Requirements 5.1, 5.2**
    """

    @given(text=st.text(min_size=1, max_size=2000))
    @settings(max_examples=200)
    def test_concatenation_equals_original(self, text: str) -> None:
        """``"".join(split_irc_message(text, max_bytes)) == text``
        for all non-empty text with default max_bytes.

        **Validates: Requirements 5.1, 5.2**
        """
        chunks = split_irc_message(text, max_bytes=450)
        assert "".join(chunks) == text

    @given(
        text=st.text(min_size=1, max_size=2000),
        max_bytes=st.integers(min_value=1, max_value=500),
    )
    @settings(max_examples=200)
    def test_concatenation_equals_original_varying_limit(self, text: str, max_bytes: int) -> None:
        """Concatenation holds for arbitrary max_bytes values.

        **Validates: Requirements 5.1, 5.2**
        """
        chunks = split_irc_message(text, max_bytes=max_bytes)
        assert "".join(chunks) == text


class TestSplitRespectsByteLimit:
    """Every chunk must encode to at most max_bytes in UTF-8.

    **Validates: Requirements 5.1, 5.3**
    """

    @given(text=st.text(min_size=1, max_size=2000))
    @settings(max_examples=200)
    def test_chunks_within_default_limit(self, text: str) -> None:
        """Each chunk ≤ 450 bytes in UTF-8 with default max_bytes.

        **Validates: Requirements 5.1, 5.3**
        """
        chunks = split_irc_message(text, max_bytes=450)
        for chunk in chunks:
            assert len(chunk.encode("utf-8")) <= 450

    @given(
        text=st.text(min_size=1, max_size=2000),
        max_bytes=st.integers(min_value=4, max_value=500),
    )
    @settings(max_examples=200)
    def test_chunks_within_varying_limit(self, text: str, max_bytes: int) -> None:
        """Each chunk ≤ max_bytes in UTF-8 for arbitrary limits.

        min_value=4 because 4 is the maximum UTF-8 character width;
        any single codepoint fits within 4 bytes.

        **Validates: Requirements 5.1, 5.3**
        """
        chunks = split_irc_message(text, max_bytes=max_bytes)
        for chunk in chunks:
            assert len(chunk.encode("utf-8")) <= max_bytes
