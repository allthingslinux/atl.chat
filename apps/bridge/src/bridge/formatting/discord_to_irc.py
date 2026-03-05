"""Convert Discord markdown to plain/IRC-formatted text for IRC."""

from __future__ import annotations

import re

# IRC formatting codes
_IRC_BOLD = "\x02"
_IRC_ITALIC = "\x1d"
_IRC_UNDERLINE = "\x1f"
_IRC_MONOSPACE = "\x11"
_IRC_RESET = "\x0f"

# Fenced code block — preserved intact for the IRC paste handler
_FENCE_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)

# URL pattern — do not modify content inside URLs
_URL_PATTERN = re.compile(
    r"https?://[^\s<>\[\]()]+(?:\([^\s<>\[\]()]*\)|[^\s<>\[\]()])*",
    re.IGNORECASE,
)

# Masked link [text](url) — capture text and url separately
_MASKED_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\)]+)\)")

# No-embed URL <https://...> — strip angle brackets
_NO_EMBED_RE = re.compile(r"<(https?://[^>]+)>")

# Headers: # / ## / ### at start of line
_HEADER_RE = re.compile(r"^#{1,3} ", re.MULTILINE)

# Subtext: -# at start of line
_SUBTEXT_RE = re.compile(r"^-# ", re.MULTILINE)

# Multi-line blockquote: >>> at start of line — everything after is quoted until end of message
# Must be matched before single-line > to avoid >>> being treated as > + >> garbage
_MULTILINE_BLOCKQUOTE_RE = re.compile(r"^>>> (.+)$", re.MULTILINE | re.DOTALL)

# Blockquote: > at start of line — convert to curly-quoted text for IRC
# (bare > at line start can confuse IRC clients that render it as a quote marker)
_BLOCKQUOTE_RE = re.compile(r"^> (.+)$", re.MULTILINE)

# Discord custom/animated emoji <:name:id> or <a:name:id> → :name:
_CUSTOM_EMOJI_RE = re.compile(r"<a?:(\w+):\d+>")

# Discord mentions — resolve to readable text
_USER_MENTION_RE = re.compile(r"<@!?(\d+)>")
_CHANNEL_MENTION_RE = re.compile(r"<#(\d+)>")
_ROLE_MENTION_RE = re.compile(r"<@&(\d+)>")

# Discord timestamps <t:UNIX:format> → human-readable
_TIMESTAMP_RE = re.compile(r"<t:(\d+)(?::[tTdDfFR])?>")

# Zero-width spaces inserted by anti-ping logic in other bridges
_ZWS_RE = re.compile(r"\u200B")


def discord_to_irc(content: str) -> str:
    """Convert Discord markdown to IRC-formatted text.

    Fenced code blocks are passed through untouched so that
    extract_code_blocks() in the IRC client can upload them to paste.
    """
    if not content:
        return content

    # Split on fenced code blocks first — pass them through verbatim
    parts: list[str] = []
    last_end = 0
    for m in _FENCE_RE.finditer(content):
        if m.start() > last_end:
            parts.append(_convert_non_fence(content[last_end : m.start()]))
        parts.append(m.group(0))
        last_end = m.end()
    if last_end < len(content):
        parts.append(_convert_non_fence(content[last_end:]))
    return "".join(parts) if parts else _convert_non_fence(content)


def _convert_non_fence(text: str) -> str:
    """Convert Discord markdown in non-fence text, preserving URLs."""
    if not text:
        return text

    # Strip zero-width spaces from anti-ping logic in other bridges
    text = _ZWS_RE.sub("", text)
    # Block-level transforms first (operate on whole text, not per-URL-segment)
    # Headers: strip leading # / ## / ###
    text = _HEADER_RE.sub("", text)
    # Subtext: strip leading -#
    text = _SUBTEXT_RE.sub("", text)

    # Blockquotes: >>> multi-line block first, then > single-line
    # >>> captures everything to end-of-message as one block; wrap each line in curly quotes
    def _quote_lines(m: re.Match) -> str:
        return "\n".join(f"\u201c{line}\u201d" if line.strip() else line for line in m.group(1).splitlines())

    text = _MULTILINE_BLOCKQUOTE_RE.sub(_quote_lines, text)
    text = _BLOCKQUOTE_RE.sub(lambda m: f"\u201c{m.group(1)}\u201d", text)
    # No-embed URLs <https://...> → strip angle brackets
    text = _NO_EMBED_RE.sub(r"\1", text)
    # Masked links: [text](url) → text (url)  — before URL splitting so url is preserved
    text = _MASKED_LINK_RE.sub(lambda m: f"{m.group(1)} ({m.group(2)})", text)
    # Custom/animated emoji <:name:id> or <a:name:id> → :name:
    text = _CUSTOM_EMOJI_RE.sub(r":\1:", text)
    # Discord mentions → readable text (best-effort without guild lookup)
    text = _USER_MENTION_RE.sub(r"@\1", text)
    text = _CHANNEL_MENTION_RE.sub(r"#\1", text)
    text = _ROLE_MENTION_RE.sub(r"@\1", text)
    # Discord timestamps → strip (no good plain-text equivalent without TZ context)
    text = _TIMESTAMP_RE.sub("", text)

    # Now process inline markdown, skipping over bare URLs
    parts: list[str] = []
    last_end = 0
    for m in _URL_PATTERN.finditer(text):
        if m.start() > last_end:
            parts.append(_convert_inline(text[last_end : m.start()]))
        parts.append(m.group(0))
        last_end = m.end()
    if last_end < len(text):
        parts.append(_convert_inline(text[last_end:]))
    return "".join(parts) if parts else _convert_inline(text)


def _convert_inline(text: str) -> str:
    """Convert Discord inline markdown to IRC formatting codes / plain text."""
    # Spoilers ||text|| → IRC black-on-black color (fg==bg = spoiler convention)
    text = re.sub(r"\|\|([^|]+)\|\|", lambda m: f"\x0301,01{m.group(1)}\x03", text)
    # Handle backslash-escaped markdown chars (Discord supports \_ \* etc.)
    # Replace each \X sequence with a private-use Unicode sentinel that contains
    # no markdown-significant characters, so subsequent patterns can't match them.
    # Private Use Area: U+E000–U+F8FF — safe to use as sentinels in bridge text.
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
    # Bold+italic ***text*** → IRC bold+italic
    text = re.sub(
        r"\*\*\*([^*]+)\*\*\*",
        lambda m: f"{_IRC_BOLD}{_IRC_ITALIC}{m.group(1)}{_IRC_ITALIC}{_IRC_BOLD}",
        text,
    )
    # Underline bold __**text**__ or __**text**__
    text = re.sub(
        r"__\*\*([^*]+)\*\*__",
        lambda m: f"{_IRC_UNDERLINE}{_IRC_BOLD}{m.group(1)}{_IRC_BOLD}{_IRC_UNDERLINE}",
        text,
    )
    # Underline italic __*text*__
    text = re.sub(
        r"__\*([^*]+)\*__",
        lambda m: f"{_IRC_UNDERLINE}{_IRC_ITALIC}{m.group(1)}{_IRC_ITALIC}{_IRC_UNDERLINE}",
        text,
    )
    # Bold **text**
    text = re.sub(r"\*\*([^*]+)\*\*", lambda m: f"{_IRC_BOLD}{m.group(1)}{_IRC_BOLD}", text)
    # Italic *text* (single asterisk, not preceded/followed by *)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", lambda m: f"{_IRC_ITALIC}{m.group(1)}{_IRC_ITALIC}", text)
    # Underline __text__
    text = re.sub(r"__([^_]+)__", lambda m: f"{_IRC_UNDERLINE}{m.group(1)}{_IRC_UNDERLINE}", text)
    # Italic _text_ — require word boundary: preceded/followed by non-word char or start/end
    text = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", lambda m: f"{_IRC_ITALIC}{m.group(1)}{_IRC_ITALIC}", text)
    # Strikethrough ~~text~~ → IRC \x1e
    text = re.sub(r"~~([^~]+)~~", lambda m: f"\x1e{m.group(1)}\x1e", text)
    # Double backtick ``text`` → IRC monospace
    text = re.sub(r"``([^`]+)``", lambda m: f"{_IRC_MONOSPACE}{m.group(1)}{_IRC_MONOSPACE}", text)
    # Single backtick inline code → IRC monospace
    text = re.sub(r"`([^`\n]+)`", lambda m: f"{_IRC_MONOSPACE}{m.group(1)}{_IRC_MONOSPACE}", text)
    # Restore escaped chars (sentinels → original chars)
    esc_restore = {v: k[1:] for k, v in esc_sentinels.items()}  # sentinel → original char
    for sentinel, ch in esc_restore.items():
        text = text.replace(sentinel, ch)
    return text
