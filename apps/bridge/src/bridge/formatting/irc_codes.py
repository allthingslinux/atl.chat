"""IRC control code parser and emitter using the formatting IR.

parse_irc_codes   — IRC control codes → FormattedText IR
emit_irc_codes    — FormattedText IR → IRC control codes
detect_irc_spoilers — detect fg==bg color regions for pipeline spoiler handling
"""

from __future__ import annotations

from bridge.formatting.primitives import FormattedText, Span, Style

# ---------------------------------------------------------------------------
# IRC control code constants
# ---------------------------------------------------------------------------

BOLD = "\x02"
COLOR = "\x03"
RESET = "\x0f"
MONOSPACE = "\x11"
REVERSE = "\x16"
ITALIC = "\x1d"
STRIKETHROUGH = "\x1e"
UNDERLINE = "\x1f"

# Set of all recognised control characters (for fast membership checks)
_CONTROL_CHARS = frozenset({BOLD, COLOR, RESET, MONOSPACE, REVERSE, ITALIC, STRIKETHROUGH, UNDERLINE})

# Map toggle control codes → Style flag.
# REVERSE (0x16) is mapped to ITALIC per design decision D1: IRC's "reverse video"
# has no visual equivalent in Discord/XMPP, and most IRC clients that use it
# intend emphasis. Mapping to ITALIC preserves the semantic intent across protocols.
_TOGGLE_MAP: dict[str, Style] = {
    BOLD: Style.BOLD,
    ITALIC: Style.ITALIC,
    UNDERLINE: Style.UNDERLINE,
    STRIKETHROUGH: Style.STRIKETHROUGH,
    MONOSPACE: Style.MONOSPACE,
    REVERSE: Style.ITALIC,  # D1: reverse → italic
}

# Reverse map: Style flag → preferred control code for the emitter.
_STYLE_TO_CODE: dict[Style, str] = {
    Style.BOLD: BOLD,
    Style.ITALIC: ITALIC,
    Style.UNDERLINE: UNDERLINE,
    Style.STRIKETHROUGH: STRIKETHROUGH,
    Style.MONOSPACE: MONOSPACE,
}

# Stable ordering for emitting toggle codes.
_STYLE_ORDER: list[Style] = [
    Style.BOLD,
    Style.ITALIC,
    Style.UNDERLINE,
    Style.STRIKETHROUGH,
    Style.MONOSPACE,
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_color_params(content: str, pos: int) -> tuple[int, int | None, int | None]:
    """Parse optional fg[,bg] digits after a \\x03 color code.

    Returns ``(new_pos, fg, bg)`` where *fg* and *bg* are ``None`` when
    the corresponding digits are absent.
    """
    fg: int | None = None
    bg: int | None = None

    # fg: 1-2 digits
    if pos < len(content) and content[pos].isdigit():
        end = pos + 1
        if end < len(content) and content[end].isdigit():
            end += 1
        fg = int(content[pos:end])
        pos = end

        # bg: comma + 1-2 digits
        if pos < len(content) and content[pos] == ",":
            next_pos = pos + 1
            if next_pos < len(content) and content[next_pos].isdigit():
                end = next_pos + 1
                if end < len(content) and content[end].isdigit():
                    end += 1
                bg = int(content[next_pos:end])
                pos = end
            # If comma is not followed by a digit, it's literal text — don't consume it.

    return pos, fg, bg


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def parse_irc_codes(content: str) -> FormattedText:
    """Parse IRC control codes into the formatting IR.

    Handles bold (0x02), italic (0x1D), underline (0x1F),
    strikethrough (0x1E), monospace (0x11), reverse (0x16 → ITALIC),
    color (0x03), and reset (0x0F).

    Color codes are stripped from the output (the IR has no color model).
    Reverse is mapped to ``Style.ITALIC`` per design decision D1.
    """
    if not content:
        return FormattedText(plain="")

    plain_parts: list[str] = []
    spans: list[Span] = []
    active: Style = Style(0)
    run_start: int = 0  # start offset in plain text of current style run
    offset: int = 0  # current length of accumulated plain text
    i: int = 0

    def _close_run() -> None:
        """If the current run has non-zero style and non-zero length, record a span."""
        nonlocal run_start
        if active and offset > run_start:
            spans.append(Span(start=run_start, end=offset, style=active))
        run_start = offset

    while i < len(content):
        ch = content[i]

        if ch in _TOGGLE_MAP:
            _close_run()
            flag = _TOGGLE_MAP[ch]
            # Toggle the flag
            active = active ^ flag
            run_start = offset
            i += 1

        elif ch == COLOR:
            _close_run()
            # Advance past \x03 and optional fg[,bg]
            i, _fg, _bg = _parse_color_params(content, i + 1)
            # Colors are stripped — no Style equivalent.
            run_start = offset

        elif ch == RESET:
            _close_run()
            active = Style(0)
            run_start = offset
            i += 1

        else:
            plain_parts.append(ch)
            offset += 1
            i += 1

    # Close any trailing run
    _close_run()

    # Merge adjacent spans with the same style
    merged: list[Span] = []
    for span in spans:
        if merged and merged[-1].end == span.start and merged[-1].style == span.style:
            merged[-1] = Span(merged[-1].start, span.end, span.style)
        else:
            merged.append(span)

    return FormattedText(plain="".join(plain_parts), spans=merged)


# ---------------------------------------------------------------------------
# Spoiler detection
# ---------------------------------------------------------------------------


def detect_irc_spoilers(content: str) -> list[tuple[int, int]]:
    """Detect fg==bg color regions in IRC content.

    Returns a list of ``(start, end)`` ranges in the *plain text*
    (control codes stripped) where the foreground color equals the
    background color.  These ranges are used by the pipeline's
    ``unwrap_spoiler`` step to set the spoiler flag.
    """
    if not content:
        return []

    ranges: list[tuple[int, int]] = []
    offset: int = 0  # plain-text position
    spoiler_start: int | None = None
    i: int = 0

    while i < len(content):
        ch = content[i]

        if ch == COLOR:
            i, fg, bg = _parse_color_params(content, i + 1)
            if fg is not None and bg is not None and fg == bg:
                # Entering a spoiler region
                if spoiler_start is None:
                    spoiler_start = offset
            else:
                # Exiting spoiler (color change or color reset)
                if spoiler_start is not None and offset > spoiler_start:
                    ranges.append((spoiler_start, offset))
                spoiler_start = None

        elif ch == RESET:
            if spoiler_start is not None and offset > spoiler_start:
                ranges.append((spoiler_start, offset))
            spoiler_start = None
            i += 1

        elif ch in _CONTROL_CHARS:
            # Other control codes — skip, don't add to plain text
            i += 1

        else:
            offset += 1
            i += 1

    # Close any trailing spoiler region
    if spoiler_start is not None and offset > spoiler_start:
        ranges.append((spoiler_start, offset))

    return ranges


# ---------------------------------------------------------------------------
# Emitter
# ---------------------------------------------------------------------------


def emit_irc_codes(ft: FormattedText) -> str:
    """Emit IRC control codes from a *FormattedText* IR.

    Inserts toggle control codes at span boundaries.  Code blocks are
    emitted inline (no fencing in IRC).
    """
    if not ft.spans and not ft.code_blocks:
        return ft.plain

    # Build style-change events keyed by position in *plain*.
    # At each position we accumulate which styles open and which close.
    opens: dict[int, Style] = {}
    closes: dict[int, Style] = {}

    for span in ft.spans:
        opens[span.start] = opens.get(span.start, Style(0)) | span.style
        closes[span.end] = closes.get(span.end, Style(0)) | span.style

    # Collect code block insertions
    cb_inserts: dict[int, str] = {}
    for cb in ft.code_blocks:
        cb_inserts[cb.start] = cb.content

    # All event positions, sorted
    positions = sorted({*opens, *closes, *cb_inserts})

    parts: list[str] = []
    active: Style = Style(0)
    prev: int = 0

    for pos in positions:
        # Emit plain text up to this position
        if pos > prev:
            parts.append(ft.plain[prev:pos])
            prev = pos

        # Process closes before opens at the same position
        closing = closes.get(pos, Style(0))
        if closing:
            # Toggle off each closing style
            for flag in _STYLE_ORDER:
                if flag in closing and flag in active:
                    parts.append(_STYLE_TO_CODE[flag])
            active = active & ~closing

        # Insert code block content
        if pos in cb_inserts:
            parts.append(cb_inserts[pos])

        opening = opens.get(pos, Style(0))
        if opening:
            # Toggle on each opening style
            for flag in _STYLE_ORDER:
                if flag in opening and flag not in active:
                    parts.append(_STYLE_TO_CODE[flag])
            active = active | opening

    # Remaining plain text
    if prev < len(ft.plain):
        parts.append(ft.plain[prev:])

    # Close any still-active styles
    for flag in _STYLE_ORDER:
        if flag in active:
            parts.append(_STYLE_TO_CODE[flag])

    return "".join(parts)
