"""Convert IRC control codes to Discord markdown."""

from __future__ import annotations

import re

# IRC control codes (per UnrealIRCd source misc.c StripControlCodesEx)
BOLD = "\x02"  # \x02 / decimal 2
COLOR = "\x03"  # \x03 / decimal 3  — mIRC color
RGB_COLOR = "\x04"  # \x04 / decimal 4  — RGB color
RESET = "\x0f"  # \x0f / decimal 15 — plain/reset
MONOSPACE = "\x11"  # \x11 / decimal 17 — monospace
REVERSE = "\x16"  # \x16 / decimal 22 — reverse video (no Discord equivalent)
ITALIC = "\x1d"  # \x1d / decimal 29
STRIKETHROUGH = "\x1e"  # \x1e / decimal 30
UNDERLINE = "\x1f"  # \x1f / decimal 31

# URL pattern - do not escape inside URLs
_URL_PATTERN = re.compile(
    r"https?://[^\s<>\[\]()]+(?:\([^\s<>\[\]()]*\)|[^\s<>\[\]()])*",
    re.IGNORECASE,
)

# IRC spoiler: \x03NN,NN where fg == bg (e.g. \x0301,01 black on black)
# Matches \x03 + 1-2 digit fg + comma + 1-2 digit bg, captures inner text up to \x03 reset
_IRC_SPOILER_RE = re.compile(r"\x03(\d{1,2}),(\d{1,2})([^\x03]*)\x03")

# Sentinel used to protect spoiler markers from the markdown escaper
_SPOILER_OPEN = "\ue010"
_SPOILER_CLOSE = "\ue011"


def _convert_irc_spoilers(content: str) -> str:
    """Replace IRC fg==bg color spans with spoiler sentinels (restored after escaping)."""

    def _replace(m: re.Match) -> str:
        fg, bg, text = int(m.group(1)), int(m.group(2)), m.group(3)
        if fg == bg:
            return f"{_SPOILER_OPEN}{text}{_SPOILER_CLOSE}"
        return m.group(0)  # leave non-spoiler colors for the general stripper

    return _IRC_SPOILER_RE.sub(_replace, content)


def irc_to_discord(content: str) -> str:
    """Convert IRC formatting to Discord markdown. Strip colors. Preserve URLs."""
    if not content:
        return content

    # Convert IRC spoiler (fg==bg color, e.g. \x0301,01) → Discord ||spoiler||
    # Must happen before general color stripping
    content = _convert_irc_spoilers(content)

    # Strip IRC color codes (\x03NN or \x03N,N or \x04RRGGBB)
    # Comma is only consumed when followed by at least one digit (background color present).
    # Per spec: \x03NN, with no bg digits → comma is literal text, not part of the code.
    content = re.sub(r"\x03\d{0,2}(?:,\d{1,2})?", "", content)
    content = re.sub(r"\x04[0-9a-fA-F]{6}", "", content)
    content = re.sub(r"\x04", "", content)
    # Strip ANSI escape sequences (e.g. from terminal-based IRC clients)
    content = re.sub(r"\x1b\[[0-9;]*[mK]", "", content)
    # Strip zero-width spaces from anti-ping logic in other bridges
    content = re.sub(r"\u200B", "", content)

    # Split by URLs to avoid escaping inside them
    result_parts: list[str] = []
    last_end = 0
    for m in _URL_PATTERN.finditer(content):
        if m.start() > last_end:
            result_parts.append(_convert_irc_codes(content[last_end : m.start()]))
        result_parts.append(m.group(0))
        last_end = m.end()
    if last_end < len(content):
        result_parts.append(_convert_irc_codes(content[last_end:]))
    result = "".join(result_parts) if result_parts else _convert_irc_codes(content)
    # Restore spoiler sentinels → Discord ||spoiler|| (after escaping so | isn't escaped)
    result = result.replace(_SPOILER_OPEN, "||").replace(_SPOILER_CLOSE, "||")
    return result


def _convert_irc_codes(text: str) -> str:
    """Convert IRC bold/italic/underline/strikethrough/monospace to Discord markdown.

    Reverse (\x16) has no Discord equivalent — stripped.
    Monospace (\x11) maps to Discord inline code backtick.
    Formatting codes inside a monospace span are stripped (not converted).
    """
    result: list[str] = []
    i = 0
    bold = False
    italic = False
    underline = False
    strikethrough = False
    monospace = False

    while i < len(text):
        ch = text[i : i + 1]
        if ch == BOLD:
            if monospace:
                # Inside monospace: strip the code, don't emit markdown
                i += 1
                continue
            if bold:
                result.append("**")
            bold = not bold
            if bold:
                result.append("**")
            i += 1
        elif ch == ITALIC:
            if monospace:
                i += 1
                continue
            if italic:
                result.append("*")
            italic = not italic
            if italic:
                result.append("*")
            i += 1
        elif ch == UNDERLINE:
            if monospace:
                i += 1
                continue
            underline = not underline
            result.append("__")
            i += 1
        elif ch == STRIKETHROUGH:
            if monospace:
                i += 1
                continue
            if strikethrough:
                result.append("~~")
            strikethrough = not strikethrough
            if strikethrough:
                result.append("~~")
            i += 1
        elif ch == MONOSPACE:
            if monospace:
                result.append("`")
            monospace = not monospace
            if monospace:
                result.append("`")
            i += 1
        elif ch == REVERSE:
            # No Discord equivalent — strip silently
            i += 1
        elif ch == RESET:
            if bold:
                result.append("**")
                bold = False
            if italic:
                result.append("*")
                italic = False
            if underline:
                result.append("__")
                underline = False
            if strikethrough:
                result.append("~~")
                strikethrough = False
            if monospace:
                result.append("`")
                monospace = False
            i += 1
        else:
            c = text[i]
            # Do NOT escape markdown chars — IRC uses control codes (\x02/\x1d/etc.)
            # for formatting, not markdown syntax. IRC users typing *text*, _text_,
            # `code`, ~~strike~~, or ||spoiler|| likely want Discord to render them.
            result.append(c)
            i += 1

    # Close any unclosed formatting
    if bold:
        result.append("**")
    if italic:
        result.append("*")
    if underline:
        result.append("__")
    if strikethrough:
        result.append("~~")
    if monospace:
        result.append("`")
    return "".join(result)
