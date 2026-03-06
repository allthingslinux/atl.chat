"""Discord markdown parser and emitter using the formatting IR.

parse_discord_markdown  — Discord markdown → FormattedText IR
emit_discord_markdown   — FormattedText IR → Discord markdown
"""

from __future__ import annotations

import re

from bridge.formatting.primitives import (
    FENCE_RE,
    URL_RE,
    CodeBlock,
    FormattedText,
    Span,
    Style,
)

# ---------------------------------------------------------------------------
# Inline pattern table — applied left-to-right, non-overlapping
# Each entry: (compiled regex, Style flags for the match)
# Every pattern must have exactly one capture group for the inner text.
# ---------------------------------------------------------------------------

_INLINE_PATTERNS: list[tuple[re.Pattern[str], Style]] = [
    # Bold + italic  ***text***
    (re.compile(r"\*\*\*(.+?)\*\*\*", re.DOTALL), Style.BOLD | Style.ITALIC),
    # Bold  **text**
    (re.compile(r"\*\*(.+?)\*\*", re.DOTALL), Style.BOLD),
    # Italic  *text*  (not preceded/followed by *)
    (re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)"), Style.ITALIC),
    # Underline  __text__
    (re.compile(r"__(.+?)__", re.DOTALL), Style.UNDERLINE),
    # Italic  _text_  (word-boundary)
    (re.compile(r"(?<!\w)_([^_\n]+)_(?!\w)"), Style.ITALIC),
    # Strikethrough  ~~text~~
    (re.compile(r"~~(.+?)~~", re.DOTALL), Style.STRIKETHROUGH),
    # Inline code  ``text``  (double backtick first)
    (re.compile(r"``([^`]+)``"), Style.MONOSPACE),
    # Inline code  `text`
    (re.compile(r"`([^`\n]+)`"), Style.MONOSPACE),
]

# Backslash-escape sentinels (PUA codepoints safe for bridge text)
_ESC_SENTINELS: dict[str, str] = {
    "\\_": "\ue001",
    "\\*": "\ue002",
    "\\`": "\ue003",
    "\\~": "\ue004",
    "\\|": "\ue005",
    "\\\\": "\ue006",
}
_ESC_RESTORE: dict[str, str] = {v: k[1:] for k, v in _ESC_SENTINELS.items()}


# ---------------------------------------------------------------------------
# Fenced code block helpers
# ---------------------------------------------------------------------------

_FENCE_DETAIL_RE = re.compile(
    r"```(\w*)\n?([\s\S]*?)```",
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def parse_discord_markdown(content: str) -> FormattedText:
    """Parse Discord markdown into the formatting IR.

    Processing order:
    1. Extract fenced code blocks (highest priority).
    2. For remaining segments, skip URLs and apply inline patterns
       left-to-right, non-overlapping.
    3. Return *FormattedText* with plain text (markers stripped),
       spans, and extracted code blocks.
    """
    if not content:
        return FormattedText(plain="")

    # --- Step 1: split on fenced code blocks ---
    segments: list[tuple[str, bool]] = []  # (text, is_fence)
    last_end = 0
    for m in FENCE_RE.finditer(content):
        if m.start() > last_end:
            segments.append((content[last_end : m.start()], False))
        segments.append((m.group(0), True))
        last_end = m.end()
    if last_end < len(content):
        segments.append((content[last_end:], False))
    if not segments:
        segments = [(content, False)]

    # --- Step 2: build plain text, spans, and code blocks ---
    plain_parts: list[str] = []
    spans: list[Span] = []
    code_blocks: list[CodeBlock] = []
    offset = 0  # running length of plain text built so far

    for text, is_fence in segments:
        if is_fence:
            m = _FENCE_DETAIL_RE.match(text)
            if m:
                lang = m.group(1) or None
                code = m.group(2)
            else:
                lang = None
                code = text[3:-3]  # strip ``` delimiters
            code_blocks.append(CodeBlock(language=lang, content=code, start=offset, end=offset))
        else:
            seg_plain, seg_spans = _parse_inline(text, offset)
            plain_parts.append(seg_plain)
            spans.extend(seg_spans)
            offset += len(seg_plain)

    return FormattedText(plain="".join(plain_parts), spans=spans, code_blocks=code_blocks)


def _parse_inline(text: str, base_offset: int) -> tuple[str, list[Span]]:
    """Strip inline Discord markdown, returning (plain_text, spans).

    URLs are preserved verbatim (no markers stripped inside them).
    Backslash-escaped markdown chars are unescaped and treated as literal.
    """
    # Replace backslash escapes with PUA sentinels
    for esc, sentinel in _ESC_SENTINELS.items():
        text = text.replace(esc, sentinel)

    # Split on URLs — process only non-URL segments
    url_ranges: list[tuple[int, int]] = [(m.start(), m.end()) for m in URL_RE.finditer(text)]

    spans: list[Span] = []
    output: list[str] = []
    pos = 0
    plain_offset = 0

    while pos < len(text):
        # Check if we're inside a URL range — if so, copy verbatim
        in_url = False
        for us, ue in url_ranges:
            if us <= pos < ue:
                chunk = text[pos:ue]
                output.append(chunk)
                plain_offset += len(chunk)
                pos = ue
                in_url = True
                break
        if in_url:
            continue

        # Find the earliest inline pattern match starting at or after pos
        best_match: re.Match[str] | None = None
        best_style: Style = Style(0)
        best_start = len(text)

        for pat, style in _INLINE_PATTERNS:
            m = pat.search(text, pos)
            if m is None:
                continue
            # Skip matches that overlap with a URL
            overlaps_url = any(not (m.end() <= us or m.start() >= ue) for us, ue in url_ranges)
            if overlaps_url:
                continue
            if m.start() < best_start:
                best_start = m.start()
                best_match = m
                best_style = style

        if best_match is None:
            output.append(text[pos:])
            break

        # Text before the match — verbatim
        output.append(text[pos : best_match.start()])
        plain_offset += best_match.start() - pos

        inner = best_match.group(1)
        span_start = base_offset + plain_offset
        output.append(inner)
        plain_offset += len(inner)
        span_end = base_offset + plain_offset

        spans.append(Span(start=span_start, end=span_end, style=best_style))
        pos = best_match.end()

    result = "".join(output)
    # Restore escaped chars
    for sentinel, ch in _ESC_RESTORE.items():
        result = result.replace(sentinel, ch)
    # Adjust span offsets for any sentinel→char length changes (both are 1 char, so no change)
    return result, spans


# ---------------------------------------------------------------------------
# Emitter
# ---------------------------------------------------------------------------

# Marker pairs for each individual style flag, ordered outermost → innermost.
# When a span has combined flags the markers are nested in this order.
_STYLE_MARKERS: list[tuple[Style, str, str]] = [
    (Style.UNDERLINE, "__", "__"),
    (Style.BOLD, "**", "**"),
    (Style.ITALIC, "*", "*"),
    (Style.STRIKETHROUGH, "~~", "~~"),
    (Style.MONOSPACE, "`", "`"),
]


def emit_discord_markdown(ft: FormattedText) -> str:
    """Reconstruct Discord markdown from a *FormattedText* IR.

    Inserts formatting markers around spans and re-inserts fenced code
    blocks at their recorded positions.
    """
    if not ft.spans and not ft.code_blocks:
        return ft.plain

    # Build a list of insertion events keyed by position in *plain*.
    # Each event: (position_in_plain, priority, marker_string)
    #   priority 0 = span open, 1 = code block, 2 = span close
    events: list[tuple[int, int, str]] = []

    for span in ft.spans:
        open_markers, close_markers = _markers_for_style(span.style)
        events.append((span.start, 0, open_markers))
        events.append((span.end, 2, close_markers))

    for cb in ft.code_blocks:
        lang = cb.language or ""
        fence = f"```{lang}\n{cb.content}```"
        events.append((cb.start, 1, fence))

    # Sort by position, then by priority (open < code < close)
    events.sort(key=lambda e: (e[0], e[1]))

    parts: list[str] = []
    prev = 0
    for pos, _prio, marker in events:
        # Emit any plain text between the previous cursor and this event
        if pos > prev:
            parts.append(ft.plain[prev:pos])
            prev = pos
        parts.append(marker)

    # Remaining plain text after the last event
    if prev < len(ft.plain):
        parts.append(ft.plain[prev:])

    return "".join(parts)


def _markers_for_style(style: Style) -> tuple[str, str]:
    """Return (opening_markers, closing_markers) for a combined Style flag.

    For BOLD | ITALIC this produces ``("***", "***")`` rather than
    nesting ``**`` and ``*`` separately, matching Discord's native syntax.
    """
    # Special case: BOLD | ITALIC without other flags → ***
    bare = style & ~Style.UNDERLINE  # underline wraps outside
    if bare == (Style.BOLD | Style.ITALIC):
        inner_open = "***"
        inner_close = "***"
        if Style.UNDERLINE in style:
            return f"__{inner_open}", f"{inner_close}__"
        return inner_open, inner_close

    open_parts: list[str] = []
    close_parts: list[str] = []
    for flag, opener, closer in _STYLE_MARKERS:
        if flag in style:
            open_parts.append(opener)
            close_parts.append(closer)
    # close_parts are reversed so nesting is correct: __**text**__
    close_parts.reverse()
    return "".join(open_parts), "".join(close_parts)
