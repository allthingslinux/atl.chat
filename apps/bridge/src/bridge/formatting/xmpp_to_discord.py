"""Convert XEP-0393 Message Styling to Discord markdown.

XEP-0393 rules (relevant subset):
  Pre-block:  line starting with ``` opens, line containing only ``` closes.
              No child spans inside pre-blocks.
  Strong:     *text*  — opener not followed by whitespace, closer not preceded by whitespace.
  Emphasis:   _text_  — same whitespace rules.
  Strike:     ~text~  — same whitespace rules.
  Mono span:  `text`  — same whitespace rules; no child spans inside.
  Quote:      > text  — pass through (Discord also renders > as block quote).
"""

from __future__ import annotations

import re

# Pre-block: ``` must be at the start of a line (possibly the only content).
# Opener: line that starts with ``` (anything after is ignored per spec).
# Closer: line containing only ```.
_PRE_BLOCK_RE = re.compile(r"(?m)^```[^\n]*\n([\s\S]*?)\n```\s*$")

# Inline span rules per XEP-0393 §6.2:
#   - opener must NOT be followed by whitespace
#   - closer must NOT be preceded by whitespace
#   - must contain at least one character between directives
#   - spans do not cross newlines (plain blocks are per-line)
# Each entry: (pattern, discord_open, discord_close)
# Mono must come first so its contents are not re-parsed.
_INLINE_RULES: list[tuple[re.Pattern[str], str, str]] = [
    # Mono `text` → `text`  (contents opaque)
    (re.compile(r"`(\S[^`\n]*?\S|\S)`"), "`", "`"),
    # Bold+italic *_text_* → ***text***  (must come before bold and italic)
    (re.compile(r"\*_(\S[^*\n]*?\S|\S)_\*"), "***", "***"),
    # Strong *text* → **text**  — opener/closer must not be adjacent to another *
    (re.compile(r"(?<!\*)\*(?!\*)(\S[^*\n]*?\S|\S)(?<!\*)\*(?!\*)"), "**", "**"),
    # Discord-style __text__ → __text__ (underline passthrough, must come before single _)
    (re.compile(r"__(\S[^_\n]*?\S|\S)__"), "__", "__"),
    # Emphasis _text_ → *text*
    (re.compile(r"(?<!_)_(?!_)(\S[^_\n]*?\S|\S)(?<!_)_(?!_)"), "*", "*"),
    # Discord-style ~~text~~ → ~~text~~ (strikethrough passthrough, must come before single ~)
    (re.compile(r"~~(\S[^~\n]*?\S|\S)~~"), "~~", "~~"),
    # Strikethrough ~text~ → ~~text~~
    (re.compile(r"(?<!~)~(?!~)(\S[^~\n]*?\S|\S)(?<!~)~(?!~)"), "~~", "~~"),
]


def xmpp_to_discord(content: str) -> str:
    """Convert XEP-0393 Message Styling to Discord markdown."""
    if not content:
        return content

    # Split on pre-blocks first — pass them through verbatim.
    # Discord uses the same ``` fence syntax so no conversion needed.
    segments: list[tuple[str, bool]] = []  # (text, is_pre)
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
            parts.append(_convert_inline(text))
    return "".join(parts)


def _convert_inline(text: str) -> str:
    """Apply inline XEP-0393 → Discord substitutions left-to-right, non-overlapping."""
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
        _, open_mark, close_mark = _INLINE_RULES[best_rule_idx]
        inner = best_match.group(1)
        output.append(f"{open_mark}{inner}{close_mark}")
        pos = best_match.end()

    return "".join(output)
