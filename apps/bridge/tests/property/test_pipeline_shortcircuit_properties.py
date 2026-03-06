"""Property-based tests for pipeline short-circuit on filter match (CP12).

**Validates: Requirements 4.2, 4.7, 4.8**

Property CP12: Pipeline Short-Circuit on Filter Match
  If content_filter returns None (match), the full pipeline returns None
  (message dropped).  Empty content is never filtered — a pipeline with
  content_filter always returns non-None for empty content.
"""

from __future__ import annotations

import re

from bridge.gateway.pipeline import Pipeline, TransformContext
from bridge.gateway.steps import (
    add_reply_fallback,
    format_convert,
    make_content_filter,
    strip_reply_fallback,
    unwrap_spoiler,
    wrap_spoiler,
)
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_PROTOCOLS = ("discord", "irc", "xmpp")

_PROTOCOL_PAIRS = st.sampled_from([(o, t) for o in _PROTOCOLS for t in _PROTOCOLS if o != t])

# Safe literal patterns that won't cause catastrophic backtracking.
_SAFE_LITERALS = st.sampled_from(["spam", "ads", "block", "drop", "filter", "banned", "nope", "reject"])

_PATTERN_LIST = st.lists(_SAFE_LITERALS, min_size=1, max_size=4).map(lambda pats: [re.compile(p) for p in pats])

# Content that is guaranteed to match at least one pattern: we pick a
# pattern literal and embed it in surrounding safe text.
_safe_word = st.from_regex(r"[a-zA-Z]{1,8}", fullmatch=True)


@st.composite
def _matching_content(draw: st.DrawFn) -> tuple[list[re.Pattern[str]], str]:
    """Return ``(patterns, content)`` where *content* matches at least one pattern."""
    patterns = draw(_PATTERN_LIST)
    # Pick one of the literal strings used to build the patterns.
    chosen = draw(st.sampled_from([p.pattern for p in patterns]))
    prefix = draw(_safe_word)
    suffix = draw(_safe_word)
    content = f"{prefix} {chosen} {suffix}"
    return patterns, content


# Dummy contexts — content_filter doesn't inspect ctx fields beyond
# origin/target, which the earlier steps use.
_CTX = st.builds(
    TransformContext,
    origin=st.sampled_from(_PROTOCOLS),
    target=st.sampled_from(_PROTOCOLS),
)


def _build_pipeline(patterns: list[re.Pattern[str]]) -> Pipeline:
    """Build the standard pipeline with content_filter as the last step."""
    return Pipeline(
        [
            strip_reply_fallback,
            unwrap_spoiler,
            format_convert,
            wrap_spoiler,
            add_reply_fallback,
            make_content_filter(patterns),
        ]
    )


# ---------------------------------------------------------------------------
# CP12 Property 1: Pipeline returns None when content matches a filter
# ---------------------------------------------------------------------------


class TestPipelineShortCircuitOnFilterMatch:
    """When content matches a filter pattern, the full pipeline returns None.

    **Validates: Requirements 4.2, 4.7, 4.8**
    """

    @given(data=_matching_content(), ctx=_CTX)
    @settings(max_examples=200)
    def test_pipeline_returns_none_on_filter_match(
        self,
        data: tuple[list[re.Pattern[str]], str],
        ctx: TransformContext,
    ) -> None:
        """Full pipeline returns None when content_filter matches.

        **Validates: Requirements 4.2, 4.7**
        """
        patterns, content = data
        pipeline = _build_pipeline(patterns)
        result = pipeline.transform(content, ctx)
        assert result is None, (
            f"Pipeline should return None for matching content: "
            f"content={content!r}, patterns={[p.pattern for p in patterns]}"
        )


# ---------------------------------------------------------------------------
# CP12 Property 2: Steps after content_filter are never called on match
# ---------------------------------------------------------------------------


class TestStepsAfterFilterNeverCalled:
    """Steps placed after content_filter are never invoked when filter matches.

    **Validates: Requirements 4.2, 4.7**
    """

    @given(data=_matching_content(), ctx=_CTX)
    @settings(max_examples=200)
    def test_trailing_step_not_called(
        self,
        data: tuple[list[re.Pattern[str]], str],
        ctx: TransformContext,
    ) -> None:
        """A sentinel step after content_filter is never reached on match.

        **Validates: Requirements 4.2, 4.7**
        """
        patterns, content = data
        called = []

        def sentinel(c: str, _ctx: TransformContext) -> str:
            called.append(True)
            return c

        pipeline = Pipeline(
            [
                strip_reply_fallback,
                unwrap_spoiler,
                format_convert,
                wrap_spoiler,
                add_reply_fallback,
                make_content_filter(patterns),
                sentinel,
            ]
        )
        result = pipeline.transform(content, ctx)
        assert result is None
        assert called == [], "Sentinel step should never be called after filter match"


# ---------------------------------------------------------------------------
# CP12 Property 3: Empty content is never filtered by the pipeline
# ---------------------------------------------------------------------------


class TestEmptyContentNeverFilteredByPipeline:
    """Pipeline with content_filter returns non-None for empty content.

    **Validates: Requirements 4.2, 4.8**
    """

    @given(
        patterns=_PATTERN_LIST,
        pair=_PROTOCOL_PAIRS,
    )
    @settings(max_examples=200)
    def test_empty_content_passes_through_pipeline(
        self,
        patterns: list[re.Pattern[str]],
        pair: tuple[str, str],
    ) -> None:
        """Empty content always passes through the full pipeline.

        **Validates: Requirements 4.2, 4.8**
        """
        origin, target = pair
        ctx = TransformContext(origin=origin, target=target)
        pipeline = _build_pipeline(patterns)
        result = pipeline.transform("", ctx)
        assert result is not None, (
            f"Pipeline should not drop empty content: patterns={[p.pattern for p in patterns]}, {origin}→{target}"
        )
