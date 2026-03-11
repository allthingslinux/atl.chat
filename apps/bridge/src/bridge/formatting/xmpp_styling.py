"""XEP-0393 Message Styling parser/emitter and XEP-0394 Message Markup emitter.

parse_xep0393   — XEP-0393 styled text → FormattedText IR
emit_xep0393    — FormattedText IR → XEP-0393 styled text
emit_xep0394    — FormattedText IR → slixmpp Markup stanza

XEP-0393 is implemented from scratch (slixmpp has no built-in plugin).
XEP-0394 uses slixmpp's stanza classes, extended with a custom StrongType
for bold (not present in slixmpp's bundled v0.2 stanzas).
"""

from __future__ import annotations

import re

from slixmpp.plugins.xep_0394.stanza import (
    BlockCode,
    Markup,
    _SpanType,
)
from slixmpp.plugins.xep_0394.stanza import (
    Span as XEP0394Span,
)
from slixmpp.xmlstream import ET
from slixmpp.xmlstream.stanzabase import register_stanza_plugin

from bridge.formatting.primitives import (
    URL_RE,
    CodeBlock,
    FormattedText,
    Span,
    Style,
)

# ---------------------------------------------------------------------------
# Custom StrongType for XEP-0394 v0.3.0+ bold support
# slixmpp's bundled stanzas only have emphasis, code, deleted.
# ---------------------------------------------------------------------------


class StrongType(_SpanType):
    """XEP-0394 v0.3.0+ ``<strong/>`` element for bold text."""

    name = "strong"
    plugin_attrib = "strong"


# Register so Span.append(StrongType()) works correctly.
register_stanza_plugin(XEP0394Span, StrongType)

# ---------------------------------------------------------------------------
# XEP-0393 constants and patterns
# ---------------------------------------------------------------------------

# Pre-block: ``` at start of a line opens, ``` alone on a line closes.
_PRE_BLOCK_RE = re.compile(r"(?m)^```[^\n]*\n([\s\S]*?)\n```\s*$")

# Fenced code detail: extract optional language hint.
_FENCE_DETAIL_RE = re.compile(r"```(\w*)\n?([\s\S]*?)```", re.MULTILINE)

# Block quote: > at start of line.
_QUOTE_RE = re.compile(r"^> (.+)$", re.MULTILINE)

# XEP-0393 inline patterns.
# Rules (from XEP-0393 §3):
#   - Styling directive must start at a word boundary (preceded by
#     whitespace, start of string, or another directive character).
#   - Closing directive must be followed by a non-alphanumeric char,
#     whitespace, or end of string.
#   - Backtick (monospace) takes priority over other inline styles.
#   - Inner text: opener must NOT be followed by whitespace, closer
#     must NOT be preceded by whitespace, at least one char inside.
#
# These rules differ from Discord markdown: Discord uses ** for bold
# while XEP-0393 uses single *. Discord's _ italic requires word
# boundaries only for single underscore, while XEP-0393 requires
# word boundaries for all directives.
#
# We use a left-to-right, non-overlapping scan (same approach as the
# markdown and IRC parsers).

# Word-boundary lookbehind for XEP-0393: start of string, whitespace,
# or another styling directive character.
_WB = r"(?:(?<=\s)|(?<=^)|(?<=[*_~`]))"

_INLINE_PATTERNS: list[tuple[re.Pattern[str], Style]] = [
    # Monospace `text` — highest priority among inline styles.
    (re.compile(r"`(\S(?:[^`]*\S)?)`(?=[^a-zA-Z0-9]|$)"), Style.MONOSPACE),
    # Bold *text*
    (re.compile(r"(?<!\*)\*(\S(?:[^*]*\S)?)\*(?!\*)(?=[^a-zA-Z0-9]|$)"), Style.BOLD),
    # Italic _text_
    (re.compile(r"(?<!_)_(\S(?:[^_]*\S)?)_(?!_)(?=[^a-zA-Z0-9]|$)"), Style.ITALIC),
    # Strikethrough ~~text~~ (Discord-style) — before single ~ so it takes precedence
    (re.compile(r"(?<!~)~~(\S(?:[^~]*\S)?)~~(?!~)(?=[^a-zA-Z0-9]|$)"), Style.STRIKETHROUGH),
    # Strikethrough ~text~ (XEP-0393 native)
    (re.compile(r"(?<!~)~(\S(?:[^~]*\S)?)~(?!~)(?=[^a-zA-Z0-9]|$)"), Style.STRIKETHROUGH),
]


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def parse_xep0393(content: str) -> FormattedText:
    """Parse XEP-0393 Message Styling into the formatting IR.

    Processing order:
    1. Extract fenced code blocks (``` ... ```) — highest priority.
    2. For remaining segments, apply inline patterns left-to-right,
       non-overlapping.  Backtick spans take priority.
    3. Block quotes (``> text``) are kept as plain text (the IR has
       no quote model; they pass through to the emitter).
    """
    if not content:
        return FormattedText(plain="")

    # --- Step 1: split on fenced code blocks ---
    segments: list[tuple[str, bool]] = []  # (text, is_fence)
    last_end = 0
    for m in _PRE_BLOCK_RE.finditer(content):
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
    offset = 0

    for text, is_fence in segments:
        if is_fence:
            m = _FENCE_DETAIL_RE.match(text)
            if m:
                lang = m.group(1) or None
                code = m.group(2)
            else:
                lang = None
                code = text[3:-3]
            code_blocks.append(CodeBlock(language=lang, content=code, start=offset, end=offset))
        else:
            seg_plain, seg_spans = _parse_inline(text, offset)
            plain_parts.append(seg_plain)
            spans.extend(seg_spans)
            offset += len(seg_plain)

    return FormattedText(plain="".join(plain_parts), spans=spans, code_blocks=code_blocks)


def _parse_inline(text: str, base_offset: int) -> tuple[str, list[Span]]:
    """Strip XEP-0393 inline styling, returning (plain_text, spans).

    URLs are detected first and passed through verbatim so that
    underscores (and other styling characters) inside URLs are not
    treated as formatting directives.
    """
    # Pre-compute URL regions to protect from inline styling.
    url_regions: list[tuple[int, int]] = [(m.start(), m.end()) for m in URL_RE.finditer(text)]

    def _overlaps_url(start: int, end: int) -> bool:
        return any(start < ue and end > us for us, ue in url_regions)

    spans: list[Span] = []
    output: list[str] = []
    pos = 0
    plain_offset = 0

    while pos < len(text):
        best_match: re.Match[str] | None = None
        best_style: Style = Style(0)
        best_start = len(text)

        for pat, style in _INLINE_PATTERNS:
            m = pat.search(text, pos)
            if m is None:
                continue
            # Skip matches that overlap with a URL region.
            if _overlaps_url(m.start(), m.end()):
                continue
            if m.start() < best_start:
                best_start = m.start()
                best_match = m
                best_style = style

        if best_match is None:
            output.append(text[pos:])
            break

        # Text before the match — verbatim.
        output.append(text[pos : best_match.start()])
        plain_offset += best_match.start() - pos

        inner = best_match.group(1)
        span_start = base_offset + plain_offset
        output.append(inner)
        plain_offset += len(inner)
        span_end = base_offset + plain_offset

        spans.append(Span(start=span_start, end=span_end, style=best_style))
        pos = best_match.end()

    return "".join(output), spans


# ---------------------------------------------------------------------------
# XEP-0393 Emitter
# ---------------------------------------------------------------------------

# Marker pairs for each individual style flag.
_XEP0393_MARKERS: list[tuple[Style, str, str]] = [
    (Style.BOLD, "*", "*"),
    (Style.ITALIC, "_", "_"),
    (Style.STRIKETHROUGH, "~", "~"),
    (Style.MONOSPACE, "`", "`"),
    # UNDERLINE has no XEP-0393 equivalent — silently dropped.
]


def emit_xep0393(ft: FormattedText) -> str:
    """Emit XEP-0393 Message Styling from a *FormattedText* IR.

    UNDERLINE spans are silently dropped (no XEP-0393 equivalent).
    Code blocks are emitted as fenced ``` blocks.
    """
    if not ft.spans and not ft.code_blocks:
        return ft.plain

    events: list[tuple[int, int, str]] = []

    for span in ft.spans:
        open_markers, close_markers = _xep0393_markers_for_style(span.style)
        if open_markers:
            events.append((span.start, 0, open_markers))
            events.append((span.end, 2, close_markers))

    for cb in ft.code_blocks:
        lang = cb.language or ""
        fence = f"```{lang}\n{cb.content}\n```"
        events.append((cb.start, 1, fence))

    events.sort(key=lambda e: (e[0], e[1]))

    parts: list[str] = []
    prev = 0
    for pos, _prio, marker in events:
        if pos > prev:
            parts.append(ft.plain[prev:pos])
            prev = pos
        parts.append(marker)

    if prev < len(ft.plain):
        parts.append(ft.plain[prev:])

    return "".join(parts)


def _xep0393_markers_for_style(style: Style) -> tuple[str, str]:
    """Return (open, close) markers for a combined Style flag."""
    open_parts: list[str] = []
    close_parts: list[str] = []
    for flag, opener, closer in _XEP0393_MARKERS:
        if flag in style:
            open_parts.append(opener)
            close_parts.append(closer)
    close_parts.reverse()
    return "".join(open_parts), "".join(close_parts)


# ---------------------------------------------------------------------------
# XEP-0394 Emitter
# ---------------------------------------------------------------------------

# Style → XEP-0394 span type name.
# UNDERLINE is intentionally absent (no XEP-0394 equivalent).
_STYLE_TO_XEP0394: dict[Style, str] = {
    Style.BOLD: "strong",
    Style.ITALIC: "emphasis",
    Style.MONOSPACE: "code",
    Style.STRIKETHROUGH: "deleted",
}


def emit_xep0394(ft: FormattedText) -> Markup:
    """Emit XEP-0394 Message Markup from a *FormattedText* IR.

    Returns a slixmpp ``Markup`` stanza element that can be appended
    to a message stanza.

    Mapping (v0.3.0+):
        BOLD → ``<strong/>``, ITALIC → ``<emphasis/>``,
        MONOSPACE → ``<code/>``, STRIKETHROUGH → ``<deleted/>``.
        UNDERLINE is dropped (no XEP-0394 equivalent).
    """
    markup = Markup()

    for span in ft.spans:
        # Decompose combined flags into individual XEP-0394 types.
        types: list[str] = []
        for flag, type_name in _STYLE_TO_XEP0394.items():
            if flag in span.style:
                types.append(type_name)

        if not types:
            # Only UNDERLINE (or empty) — skip.
            continue

        xep_span = XEP0394Span()
        xep_span["start"] = span.start
        xep_span["end"] = span.end

        for type_name in types:
            xep_span.xml.append(ET.Element(f"{{urn:xmpp:markup:0}}{type_name}"))

        markup.append(xep_span)

    for cb in ft.code_blocks:
        bcode = BlockCode()
        bcode["start"] = cb.start
        bcode["end"] = cb.start + len(cb.content) if cb.content else cb.start
        markup.append(bcode)

    return markup
