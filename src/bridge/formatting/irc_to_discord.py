"""Convert IRC control codes to Discord markdown."""

from __future__ import annotations

import re

# IRC control codes
BOLD = "\x02"
COLOR = "\x03"
ITALIC = "\x1D"
UNDERLINE = "\x1F"
RESET = "\x0F"

# URL pattern - do not escape inside URLs
_URL_PATTERN = re.compile(
    r"https?://[^\s<>\[\]()]+(?:\([^\s<>\[\]()]*\)|[^\s<>\[\]()])*",
    re.IGNORECASE,
)


def irc_to_discord(content: str) -> str:
    """Convert IRC formatting to Discord markdown. Strip colors. Preserve URLs."""
    if not content:
        return content

    # Strip IRC color codes (\x03NN or \x03N,N or \x04RRGGBB)
    content = re.sub(r"\x03\d{0,2}(?:,\d{0,2})?", "", content)
    content = re.sub(r"\x04[0-9a-fA-F]{6}", "", content)
    content = re.sub(r"\x04", "", content)

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
    return "".join(result_parts) if result_parts else _convert_irc_codes(content)


def _convert_irc_codes(text: str) -> str:
    """Convert IRC bold/italic/underline to Discord markdown."""
    result: list[str] = []
    i = 0
    bold = False
    italic = False
    underline = False

    while i < len(text):
        if text[i : i + 1] == BOLD:
            if bold:
                result.append("**")
            bold = not bold
            if bold:
                result.append("**")
            i += 1
        elif text[i : i + 1] == ITALIC:
            if italic:
                result.append("*")
            italic = not italic
            if italic:
                result.append("*")
            i += 1
        elif text[i : i + 1] == UNDERLINE:
            underline = not underline
            # Discord has no underline; use __ for emphasis
            if underline:
                result.append("__")
            else:
                result.append("__")
            i += 1
        elif text[i : i + 1] == RESET:
            if bold:
                result.append("**")
                bold = False
            if italic:
                result.append("*")
                italic = False
            if underline:
                result.append("__")
                underline = False
            i += 1
        else:
            c = text[i]
            # Escape Discord markdown chars outside URLs
            if c in "*_`~|":
                result.append("\\")
            result.append(c)
            i += 1

    # Close any unclosed formatting
    if bold:
        result.append("**")
    if italic:
        result.append("*")
    if underline:
        result.append("__")
    return "".join(result)
