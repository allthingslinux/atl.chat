"""Property-based tests for parse-emit-parse roundtrip (CP13).

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

Property CP13: Formatting Parse-Emit-Parse Round-Trip
  For any valid FormattedText object and for any protocol, emitting the IR
  to that protocol's format and then parsing it back shall produce an
  equivalent FormattedText object (accounting for known lossy conversions
  like UNDERLINE→XMPP).
"""

from __future__ import annotations

from bridge.formatting.irc_codes import emit_irc_codes, parse_irc_codes
from bridge.formatting.markdown import emit_discord_markdown, parse_discord_markdown
from bridge.formatting.primitives import FormattedText, Span, Style
from bridge.formatting.xmpp_styling import emit_xep0393, parse_xep0393
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Protocol-specific emit/parse pairs.
_EMIT_PARSE: dict[str, tuple] = {
    "discord": (emit_discord_markdown, parse_discord_markdown),
    "irc": (emit_irc_codes, parse_irc_codes),
    "xmpp": (emit_xep0393, parse_xep0393),
}

# Styles that each protocol can roundtrip.  The parsers use flat left-to-right
# scanning, so only styles expressible without nesting survive emit→parse.
#
# Discord: single flags + BOLD|ITALIC (***text***).  Nesting __**text**__
#          is NOT parsed back correctly (parser is non-recursive).
# IRC:     all single flags (toggle-based, no nesting issues).
# XMPP:    single flags except UNDERLINE (dropped by emitter).
_ROUNDTRIPPABLE_STYLES: dict[str, list[Style]] = {
    "discord": [
        Style.BOLD,
        Style.ITALIC,
        Style.UNDERLINE,
        Style.STRIKETHROUGH,
        Style.MONOSPACE,
        Style.BOLD | Style.ITALIC,  # *** syntax
    ],
    "irc": [
        Style.BOLD,
        Style.ITALIC,
        Style.UNDERLINE,
        Style.STRIKETHROUGH,
        Style.MONOSPACE,
    ],
    "xmpp": [
        Style.BOLD,
        Style.ITALIC,
        Style.STRIKETHROUGH,
        Style.MONOSPACE,
    ],
}

_protocols = st.sampled_from(["discord", "irc", "xmpp"])

# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Safe word: alphanumeric only, avoids all formatting markers.
_word = st.from_regex(r"[a-zA-Z][a-zA-Z0-9]{0,7}", fullmatch=True)


@st.composite
def _formatted_text_for_protocol(draw: st.DrawFn, protocol: str) -> FormattedText:
    """Generate a FormattedText with space-separated words and non-overlapping
    spans aligned to word boundaries.

    Word-boundary alignment ensures formatting markers are parseable by the
    target protocol (XEP-0393 requires non-alphanumeric after closing markers,
    Discord markdown has similar boundary rules).
    """
    num_words = draw(st.integers(min_value=2, max_value=8))
    words = [draw(_word) for _ in range(num_words)]
    plain = " ".join(words)

    # Compute word boundary positions: (start, end) for each word.
    boundaries: list[tuple[int, int]] = []
    offset = 0
    for w in words:
        boundaries.append((offset, offset + len(w)))
        offset += len(w) + 1  # +1 for the space

    # Pick a subset of word indices to format as spans.
    num_spans = draw(st.integers(min_value=0, max_value=min(3, num_words)))
    if num_spans == 0:
        return FormattedText(plain=plain, spans=[])

    # Choose distinct word indices for spans (non-overlapping).
    chosen = sorted(
        draw(
            st.lists(
                st.integers(min_value=0, max_value=num_words - 1),
                min_size=num_spans,
                max_size=num_spans,
                unique=True,
            )
        )
    )

    styles = _ROUNDTRIPPABLE_STYLES[protocol]
    style_st = st.sampled_from(styles)

    spans: list[Span] = []
    for idx in chosen:
        start, end = boundaries[idx]
        style = draw(style_st)
        spans.append(Span(start=start, end=end, style=style))

    return FormattedText(plain=plain, spans=spans)


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------


def _normalize_spans(spans: list[Span]) -> list[tuple[int, int, Style]]:
    """Normalize spans for comparison: sort by start, merge adjacent same-style."""
    if not spans:
        return []

    sorted_spans = sorted(spans, key=lambda s: (s.start, s.end))

    merged: list[tuple[int, int, Style]] = []
    for s in sorted_spans:
        if s.start >= s.end:
            continue
        if merged and merged[-1][2] == s.style and merged[-1][1] >= s.start:
            merged[-1] = (merged[-1][0], max(merged[-1][1], s.end), s.style)
        else:
            merged.append((s.start, s.end, s.style))

    return merged


def _filter_underline(spans: list[Span]) -> list[Span]:
    """Remove UNDERLINE from span styles; drop spans that become empty."""
    result: list[Span] = []
    for s in spans:
        style = s.style & ~Style.UNDERLINE
        if style:
            result.append(Span(start=s.start, end=s.end, style=style))
    return result


# ---------------------------------------------------------------------------
# Property test
# ---------------------------------------------------------------------------


class TestParseEmitParseRoundtrip:
    """CP13: Emit then parse for the same protocol produces equivalent FormattedText.

    **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
    """

    @given(data=st.data(), protocol=_protocols)
    @settings(max_examples=200)
    def test_emit_parse_roundtrip(self, data: st.DataObject, protocol: str) -> None:
        """For any valid FormattedText, emitting to a protocol's format and
        parsing back produces equivalent FormattedText.

        UNDERLINE is dropped for XMPP (known lossy conversion).

        **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
        """
        ft = data.draw(_formatted_text_for_protocol(protocol))
        emitter, parser = _EMIT_PARSE[protocol]

        # Emit IR → protocol format.
        emitted = emitter(ft)

        # Parse protocol format → IR.
        reparsed = parser(emitted)

        # Determine expected spans accounting for lossy conversions.
        expected_spans = _filter_underline(ft.spans) if protocol == "xmpp" else list(ft.spans)

        # Plain text must be identical.
        assert reparsed.plain == ft.plain, (
            f"Plain text mismatch for {protocol}: "
            f"original={ft.plain!r}, reparsed={reparsed.plain!r}, "
            f"emitted={emitted!r}"
        )

        # Spans must be equivalent after normalization.
        expected_norm = _normalize_spans(expected_spans)
        actual_norm = _normalize_spans(reparsed.spans)

        assert actual_norm == expected_norm, (
            f"Span mismatch for {protocol}: "
            f"expected={expected_norm!r}, actual={actual_norm!r}, "
            f"emitted={emitted!r}, original_spans={ft.spans!r}"
        )
