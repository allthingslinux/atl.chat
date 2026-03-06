"""Convert Discord markdown to plain text + XEP-0394 markup spans for XMPP.

This is the ONLY legacy direct converter kept after the IR-based refactor.
It's retained because the XMPP adapter needs dual output: both XEP-0393
styled body text (for clients like Gajim that render Message Styling) AND
XEP-0394 markup spans (for clients that support Message Markup). The IR-based
converter only produces one output format at a time, so this module handles
the Discord-specific transforms (emoji, mentions, timestamps) plus the dual
XEP-0393/XEP-0394 output in a single pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Fenced code block: ```[lang]\n...\n``` — handled separately (paste upload)
_FENCE_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)

# Masked link [text](url)
_MASKED_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\)]+)\)")

# No-embed URL <https://...> — strip angle brackets
_NO_EMBED_RE = re.compile(r"<(https?://[^>]+)>")

# Headers: # / ## / ### at start of line
_HEADER_RE = re.compile(r"^#{1,3} ", re.MULTILINE)

# Subtext: -# at start of line
_SUBTEXT_RE = re.compile(r"^-# ", re.MULTILINE)

# Discord custom/animated emoji <:name:id> or <a:name:id> → :name:
_CUSTOM_EMOJI_RE = re.compile(r"<a?:(\w+):\d+>")

# Discord mentions — resolve to readable text
_USER_MENTION_RE = re.compile(r"<@!?(\d+)>")
_CHANNEL_MENTION_RE = re.compile(r"<#(\d+)>")
_ROLE_MENTION_RE = re.compile(r"<@&(\d+)>")

# Discord timestamps <t:UNIX:format> → strip
_TIMESTAMP_RE = re.compile(r"<t:(\d+)(?::[tTdDfFR])?>")

# Zero-width spaces from anti-ping logic in other bridges
_ZWS_RE = re.compile(r"\u200B")


@dataclass
class MarkupSpan:
    start: int
    end: int
    types: list[str]  # e.g. ["emphasis"], ["strong"], ["code"], ["deleted"]


@dataclass
class BlockCode:
    start: int
    end: int
    language: str = ""


@dataclass
class XMPPMarkup:
    body: str
    spans: list[MarkupSpan] = field(default_factory=list)
    bcodes: list[BlockCode] = field(default_factory=list)
    # XEP-0393 styled body (e.g. *bold*, _italic_) for clients like Gajim
    # that render Message Styling but not XEP-0394 markup elements.
    # When None, no styling markers were present and body is used as-is.
    styled_body: str | None = None

    @property
    def has_markup(self) -> bool:
        return bool(self.spans or self.bcodes)


def discord_to_xmpp(content: str) -> XMPPMarkup:
    """Convert Discord markdown to plain body + XEP-0394 markup metadata.

    Fenced code blocks are passed through intact (the XMPP adapter uploads them
    to paste before calling this). Everything else is stripped to plain text and
    the formatting positions are recorded as XEP-0394 spans/bcodes.
    """
    if not content:
        return XMPPMarkup(body=content)

    # Split on fenced code blocks — pass them through verbatim (paste handler owns them)
    segments: list[tuple[str, bool]] = []  # (text, is_fence)
    last_end = 0
    for m in _FENCE_RE.finditer(content):
        if m.start() > last_end:
            segments.append((content[last_end : m.start()], False))
        segments.append((m.group(0), True))
        last_end = m.end()
    if last_end < len(content):
        segments.append((content[last_end:], False))
    if not segments:
        segments = [(content, False)]

    # Block-level transforms on non-fence segments before span parsing
    clean_segments: list[tuple[str, bool]] = []
    for seg_text, is_fence in segments:
        if is_fence:
            clean_segments.append((seg_text, True))
        else:
            cleaned = _ZWS_RE.sub("", seg_text)
            cleaned = _HEADER_RE.sub("", cleaned)
            cleaned = _SUBTEXT_RE.sub("", cleaned)
            cleaned = _NO_EMBED_RE.sub(r"\1", cleaned)
            cleaned = _MASKED_LINK_RE.sub(lambda m: f"{m.group(1)} ({m.group(2)})", cleaned)
            cleaned = _CUSTOM_EMOJI_RE.sub(r":\1:", cleaned)
            cleaned = _USER_MENTION_RE.sub(r"@\1", cleaned)
            cleaned = _CHANNEL_MENTION_RE.sub(r"#\1", cleaned)
            cleaned = _ROLE_MENTION_RE.sub(r"@\1", cleaned)
            cleaned = _TIMESTAMP_RE.sub("", cleaned)
            clean_segments.append((cleaned, False))

    result_parts: list[str] = []
    styled_parts: list[str] = []
    all_spans: list[MarkupSpan] = []
    offset = 0

    for text, is_fence in clean_segments:
        if is_fence:
            result_parts.append(text)
            styled_parts.append(text)
            offset += len(text)
        else:
            plain, spans = _parse_markdown(text, offset)
            result_parts.append(plain)
            all_spans.extend(spans)
            offset += len(plain)
            styled_parts.append(_to_xep0393(text))

    body = "".join(result_parts)
    styled = "".join(styled_parts)
    # Only set styled_body when it differs from body (i.e. there was markup to convert)
    styled_body = styled if styled != body else None
    return XMPPMarkup(body=body, spans=all_spans, styled_body=styled_body)


# Ordered list of (pattern, span_types) — applied left to right, non-overlapping
# Each pattern must have exactly one capture group containing the inner text.
_INLINE_PATTERNS: list[tuple[re.Pattern[str], list[str]]] = [
    # Bold+italic ***text***
    (re.compile(r"\*\*\*([^*]+)\*\*\*"), ["strong", "emphasis"]),
    # Underline bold+italic __***text***__
    (re.compile(r"__\*\*\*([^*]+)\*\*\*__"), ["strong", "emphasis"]),
    # Underline bold __**text**__
    (re.compile(r"__\*\*([^*]+)\*\*__"), ["strong"]),
    # Underline italic __*text*__
    (re.compile(r"__\*([^*]+)\*__"), ["emphasis"]),
    # Bold **text**
    (re.compile(r"\*\*([^*]+)\*\*"), ["strong"]),
    # Italic *text* (single, not preceded/followed by *)
    (re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)"), ["emphasis"]),
    # Underline __text__ — XEP-0394 has no underline; strip markers, emit no span
    (re.compile(r"__([^_]+)__"), []),
    # Italic _text_ (single) — require word boundary
    (re.compile(r"(?<!\w)_([^_\n]+)_(?!\w)"), ["emphasis"]),
    # Strikethrough ~~text~~
    (re.compile(r"~~([^~]+)~~"), ["deleted"]),
    # Inline code `text`
    (re.compile(r"`([^`\n]+)`"), ["code"]),
    # Double backtick ``text``
    (re.compile(r"``([^`]+)``"), ["code"]),
    # Spoilers ||text|| — strip markers, no XEP-0394 span (handled by XEP-0382)
    (re.compile(r"\|\|([^|]+)\|\|"), []),
]


def _parse_markdown(text: str, base_offset: int) -> tuple[str, list[MarkupSpan]]:
    """Strip Discord markdown from text, returning (plain_text, spans).

    Spans have absolute character offsets (base_offset + position in plain_text).
    Handles backslash-escaped markdown chars (\\_ \\* etc.) — they are unescaped
    and treated as literal text, not formatting delimiters.
    """
    # Replace backslash-escaped markdown chars with private-use sentinels
    # so they are invisible to all pattern matching, then restore at the end.
    esc_sentinels = {
        "\\_": "\ue001",
        "\\*": "\ue002",
        "\\`": "\ue003",
        "\\~": "\ue004",
        "\\|": "\ue005",
        "\\\\": "\ue006",
    }
    for esc, sentinel in esc_sentinels.items():
        text = text.replace(esc, sentinel)
    esc_restore = {v: k[1:] for k, v in esc_sentinels.items()}

    spans: list[MarkupSpan] = []
    # We process the text iteratively, consuming matches left-to-right
    # and building the plain output with adjusted offsets.
    output: list[str] = []
    pos = 0
    plain_offset = 0  # current length of output so far

    # Build a combined scanner: find the earliest match across all patterns
    while pos < len(text):
        best_match = None
        best_pattern_idx = -1
        best_start = len(text)

        for i, (pat, _) in enumerate(_INLINE_PATTERNS):
            m = pat.search(text, pos)
            if m and m.start() < best_start:
                best_start = m.start()
                best_match = m
                best_pattern_idx = i

        if best_match is None:
            # No more markdown — append remainder
            output.append(text[pos:])
            break

        # Append text before the match verbatim
        output.append(text[pos : best_match.start()])
        plain_offset += best_match.start() - pos

        inner = best_match.group(1)
        span_types = _INLINE_PATTERNS[best_pattern_idx][1]

        span_start = base_offset + plain_offset
        output.append(inner)
        plain_offset += len(inner)
        span_end = base_offset + plain_offset

        if span_types:
            spans.append(MarkupSpan(start=span_start, end=span_end, types=span_types))

        pos = best_match.end()

    result = "".join(output)
    # Restore escaped chars
    for sentinel, ch in esc_restore.items():
        result = result.replace(sentinel, ch)
    return result, spans


# ---------------------------------------------------------------------------
# XEP-0393 styled body generation
# Converts Discord markdown to XEP-0393 Message Styling syntax so that
# clients like Gajim (which render XEP-0393 but not XEP-0394) show formatting.
# Discord → XEP-0393 mapping:
#   **bold**        → *bold*
#   *italic*        → _italic_
#   _italic_        → _italic_
#   ***bold italic*** → *_bold italic_*
#   ~~strike~~      → ~strike~
#   `code`          → `code`  (unchanged)
#   __underline__   → underline  (no XEP-0393 equivalent, strip markers)
#   ||spoiler||     → spoiler    (strip markers)
# ---------------------------------------------------------------------------

_XEP0393_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Bold+italic ***text*** → *_text_*  (must be before bold and italic)
    (re.compile(r"\*\*\*([^*]+)\*\*\*"), r"*_\1_*"),
    # Underline bold+italic __***text***__ → *_text_*
    (re.compile(r"__\*\*\*([^*]+)\*\*\*__"), r"*_\1_*"),
    # Underline bold __**text**__ → *text*
    (re.compile(r"__\*\*([^*]+)\*\*__"), r"*\1*"),
    # Underline italic __*text*__ → _text_
    (re.compile(r"__\*([^*]+)\*__"), r"_\1_"),
    # Bold **text** → *text*  (must be before italic *text*)
    (re.compile(r"\*\*([^*]+)\*\*"), r"*\1*"),
    # Italic *text* → _text_  (single asterisk, not preceded/followed by *)
    (re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)"), r"_\1_"),
    # Underline __text__ → text (no XEP-0393 equivalent)
    (re.compile(r"__([^_]+)__"), r"\1"),
    # Italic _text_ → _text_ (already correct, keep as-is)
    # Strikethrough ~~text~~ → ~text~
    (re.compile(r"~~([^~]+)~~"), r"~\1~"),
    # Spoilers ||text|| → text (strip markers)
    (re.compile(r"\|\|([^|]+)\|\|"), r"\1"),
    # Double backtick ``text`` → `text`
    (re.compile(r"``([^`]+)``"), r"`\1`"),
]


def _to_xep0393(text: str) -> str:
    """Convert Discord markdown in text to XEP-0393 Message Styling syntax.

    Uses a single left-to-right pass so that converted output (e.g. *bold*)
    is not re-processed by later patterns (e.g. italic *text*).
    """
    output: list[str] = []
    pos = 0
    while pos < len(text):
        best_match = None
        best_idx = -1
        best_start = len(text)
        for i, (pat, _) in enumerate(_XEP0393_PATTERNS):
            m = pat.search(text, pos)
            if m and m.start() < best_start:
                best_start = m.start()
                best_match = m
                best_idx = i
        if best_match is None:
            output.append(text[pos:])
            break
        output.append(text[pos : best_match.start()])
        _, repl = _XEP0393_PATTERNS[best_idx]
        output.append(best_match.expand(repl))
        pos = best_match.end()
    return "".join(output)
