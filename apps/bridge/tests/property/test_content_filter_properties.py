"""Property-based tests for content filter determinism (CP6).

**Validates: Requirements 4.7, 4.8**

Property CP6: Content Filter Determinism
  For any content and any set of filter patterns, calling the content filter
  twice on the same content produces the same result (determinism/idempotence),
  and the content filter never returns None for empty content.
"""

from __future__ import annotations

import re

from bridge.gateway.pipeline import TransformContext
from bridge.gateway.steps import make_content_filter
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Strategies — generate simple regex patterns that won't cause catastrophic
# backtracking or re.error.
# ---------------------------------------------------------------------------

_SAFE_LITERALS = st.sampled_from(["spam", "ads", "hello", "world", "foo", "bar", "test", "block", "drop", "filter"])
_WORD_BOUNDARY = _SAFE_LITERALS.map(lambda w: rf"\b{w}\b")
_ANCHORED_START = _SAFE_LITERALS.map(lambda w: f"^{w}")
_CHAR_CLASS = st.sampled_from([r"[a-z]+", r"[0-9]+", r"[A-Za-z]+", r"\d+", r"\w+"])

_VALID_PATTERN = st.one_of(_SAFE_LITERALS, _WORD_BOUNDARY, _ANCHORED_START, _CHAR_CLASS)

_PATTERN_LIST = st.lists(_VALID_PATTERN, min_size=0, max_size=5).map(lambda pats: [re.compile(p) for p in pats])

# Dummy context — content_filter doesn't inspect ctx fields.
_CTX = st.sampled_from(
    [
        TransformContext(origin="discord", target="irc"),
        TransformContext(origin="irc", target="xmpp"),
        TransformContext(origin="xmpp", target="discord"),
    ]
)


# ---------------------------------------------------------------------------
# CP6 Property 1: Content filter determinism / idempotence
# ---------------------------------------------------------------------------


class TestContentFilterDeterminism:
    """Calling the content filter twice on the same input yields the same result.

    **Validates: Requirements 4.7, 4.8**
    """

    @given(
        patterns=_PATTERN_LIST,
        content=st.text(min_size=0, max_size=300),
        ctx=_CTX,
    )
    @settings(max_examples=200)
    def test_filter_is_idempotent(
        self,
        patterns: list[re.Pattern[str]],
        content: str,
        ctx: TransformContext,
    ) -> None:
        """``content_filter(content, ctx)`` returns the same result on repeated calls.

        **Validates: Requirements 4.7, 4.8**
        """
        step = make_content_filter(patterns)
        first = step(content, ctx)
        second = step(content, ctx)
        assert first == second


# ---------------------------------------------------------------------------
# CP6 Property 2: Empty content is never filtered
# ---------------------------------------------------------------------------


class TestEmptyContentNeverFiltered:
    """``content_filter("")`` never returns None for any set of patterns.

    **Validates: Requirements 4.7, 4.8**
    """

    @given(
        patterns=_PATTERN_LIST,
        ctx=_CTX,
    )
    @settings(max_examples=200)
    def test_empty_content_passes_through(
        self,
        patterns: list[re.Pattern[str]],
        ctx: TransformContext,
    ) -> None:
        """Empty content is never dropped regardless of filter patterns.

        **Validates: Requirements 4.7, 4.8**
        """
        step = make_content_filter(patterns)
        result = step("", ctx)
        assert result is not None
        assert result == ""
