"""Convert XEP-0393 Message Styling to IRC control codes."""

from __future__ import annotations

import re

# IRC formatting codes
_B = "\x02"  # bold
_I = "\x1d"  # italic
_S = "\x1e"  # strikethrough
_U = "\x1f"  # underline
_M = "\x11"  # monospace
_R = "\x0f"  # reset
# IRC spoiler: black foreground on black background (fg==bg convention)
_SPOILER_OPEN = "\x0301,01"
_SPOILER_CLOSE = "\x03"

# Pre-block: same as xmpp_to_discord — pass through verbatim
_PRE_BLOCK_RE = re.compile(r"(?m)^```[^\n]*\n([\s\S]*?)\n```\s*$")

# XEP-0393 block quote: > at start of line → curly-quoted text for IRC
_BLOCKQUOTE_RE = re.compile(r"^> (.+)$", re.MULTILINE)

# Inline rules: (pattern, irc_open, irc_close)
# Mono first — contents are opaque.
# Bold+italic *_text_* must come before bold *text* and italic _text_.
_INLINE_RULES: list[tuple[re.Pattern[str], str, str]] = [
    # Mono `text` → \x11text\x11
    (re.compile(r"`(\S[^`\n]*?\S|\S)`"), _M, _M),
    # Bold+italic *_text_* → \x02\x1dtext\x1d\x02
    (re.compile(r"\*_(\S[^*\n]*?\S|\S)_\*"), f"{_B}{_I}", f"{_I}{_B}"),
    # Discord-style ***text*** → \x02\x1dtext\x1d\x02 (must come before ** and *)
    (re.compile(r"\*\*\*(\S[^*\n]*?\S|\S)\*\*\*"), f"{_B}{_I}", f"{_I}{_B}"),
    # Discord-style **text** → \x02text\x02 (must come before single * bold)
    (re.compile(r"\*\*(\S[^*\n]*?\S|\S)\*\*"), _B, _B),
    # Bold *text* → \x02text\x02  — lone * only, not adjacent to another *
    (re.compile(r"(?<!\*)\*(?!\*)(\S[^*\n]*?\S|\S)(?<!\*)\*(?!\*)"), _B, _B),
    # Discord-style __text__ → \x1ftext\x1f (underline, must come before single _ italic)
    (re.compile(r"__(\S[^_\n]*?\S|\S)__"), _U, _U),
    # Italic _text_ → \x1dtext\x1d  — lone _ only, not adjacent to another _
    (re.compile(r"(?<!_)_(?!_)(\S[^_\n]*?\S|\S)(?<!_)_(?!_)"), _I, _I),
    # Discord-style ~~text~~ → \x1etext\x1e (strikethrough, must come before single ~)
    (re.compile(r"~~(\S[^~\n]*?\S|\S)~~"), _S, _S),
    # Strikethrough ~text~ → \x1etext\x1e  — lone ~ only, not adjacent to another ~
    (re.compile(r"(?<!~)~(?!~)(\S[^~\n]*?\S|\S)(?<!~)~(?!~)"), _S, _S),
    # Discord-style ||text|| → IRC spoiler (black-on-black)
    (re.compile(r"\|\|(.+?)\|\|"), _SPOILER_OPEN, _SPOILER_CLOSE),
]


def xmpp_to_irc(content: str) -> str:
    """Convert XEP-0393 Message Styling to IRC formatting control codes."""
    if not content:
        return content

    # Split on pre-blocks — pass them through verbatim
    segments: list[tuple[str, bool]] = []
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

    parts: list[str] = []
    for text, is_pre in segments:
        if is_pre:
            parts.append(text)
        else:
            # Block-level: convert > blockquotes to curly-quoted text
            converted = _BLOCKQUOTE_RE.sub(lambda m: f"\u201c{m.group(1)}\u201d", text)
            parts.append(_convert_inline(converted))
    return "".join(parts)


def _convert_inline(text: str) -> str:
    """Apply XEP-0393 → IRC substitutions left-to-right, non-overlapping."""
    output: list[str] = []
    pos = 0

    while pos < len(text):
        best_match: re.Match[str] | None = None
        best_rule_idx = -1
        best_start = len(text)

        for i, (pat, _, _) in enumerate(_INLINE_RULES):
            m = pat.search(text, pos)
            if m and m.start() < best_start:
                best_start = m.start()
                best_match = m
                best_rule_idx = i

        if best_match is None:
            output.append(text[pos:])
            break

        output.append(text[pos : best_match.start()])
        _, open_code, close_code = _INLINE_RULES[best_rule_idx]
        inner = best_match.group(1)
        # Recursively convert inner content for non-mono spans
        if open_code != _M:
            inner = _convert_inline(inner)
        output.append(f"{open_code}{inner}{close_code}")
        pos = best_match.end()

    return "".join(output)
