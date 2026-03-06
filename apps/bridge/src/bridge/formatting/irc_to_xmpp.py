"""Convert IRC control codes to XEP-0393 Message Styling for XMPP."""

from __future__ import annotations

import re

# IRC control codes
_BOLD = "\x02"
_COLOR = "\x03"
_RGB_COLOR = "\x04"
_RESET = "\x0f"
_MONOSPACE = "\x11"
_REVERSE = "\x16"
_ITALIC = "\x1d"
_STRIKETHROUGH = "\x1e"
_UNDERLINE = "\x1f"

# Strip mIRC color codes \x03NN,NN and RGB \x04RRGGBB
# Comma only consumed when followed by at least one digit (background color present).
_COLOR_RE = re.compile(r"\x03\d{0,2}(?:,\d{1,2})?")
_RGB_RE = re.compile(r"\x04[0-9a-fA-F]{6}")
_RGB_BARE_RE = re.compile(r"\x04")
# Strip ANSI escape sequences (e.g. from terminal-based IRC clients)
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mK]")


def irc_to_xmpp(content: str) -> str:
    """Convert IRC formatting control codes to XEP-0393 Message Styling.

    Mapping:
      \\x02 bold        → *text*
      \\x1d italic      → _text_
      \\x1e strikethrough → ~text~
      \\x11 monospace   → `text`
      \\x1f underline   → (no XEP-0393 equivalent, stripped)
      \\x16 reverse     → (no equivalent, stripped)
      \\x03 color       → stripped
      \\x04 RGB color   → stripped
      \\x0f reset       → closes all open spans
    """
    if not content:
        return content

    # Strip color codes first (they have variable-length arguments)
    content = _COLOR_RE.sub("", content)
    content = _RGB_RE.sub("", content)
    content = _RGB_BARE_RE.sub("", content)
    content = _ANSI_RE.sub("", content)
    # Strip zero-width spaces from anti-ping logic in other bridges
    content = content.replace("\u200b", "")

    result: list[str] = []
    bold = False
    italic = False
    strike = False
    mono = False
    # underline and reverse have no XEP-0393 equivalent — track to consume the codes

    i = 0
    while i < len(content):
        ch = content[i]

        if ch == _BOLD:
            if mono:
                result.append(ch)  # inside monospace, pass through literally
            else:
                if bold:
                    result.append("*")
                bold = not bold
                if bold:
                    result.append("*")
        elif ch == _ITALIC:
            if mono:
                result.append(ch)
            else:
                if italic:
                    result.append("_")
                italic = not italic
                if italic:
                    result.append("_")
        elif ch == _STRIKETHROUGH:
            if mono:
                result.append(ch)
            else:
                if strike:
                    result.append("~")
                strike = not strike
                if strike:
                    result.append("~")
        elif ch == _MONOSPACE:
            if mono:
                result.append("`")
            mono = not mono
            if mono:
                result.append("`")
        elif ch in (_UNDERLINE, _REVERSE):
            pass  # no XEP-0393 equivalent, consume silently
        elif ch == _RESET:
            if bold:
                result.append("*")
                bold = False
            if italic:
                result.append("_")
                italic = False
            if strike:
                result.append("~")
                strike = False
            if mono:
                result.append("`")
                mono = False
        else:
            result.append(ch)

        i += 1

    # Close any unclosed spans
    if bold:
        result.append("*")
    if italic:
        result.append("_")
    if strike:
        result.append("~")
    if mono:
        result.append("`")

    return _fix_xep0393_whitespace("".join(result))


# XEP-0393 §6.2: opener must not be followed by whitespace,
# closer must not be preceded by whitespace.
# Fix spans like "_  hello _" → "  _hello_ " and "* hi *" → " *hi* ".
_XEP0393_WS_FIX_RE = re.compile(
    r"([*_~`])([ \t]+)(.*?)([ \t]+)(\1)",
    re.DOTALL,
)
# Spans containing only whitespace (e.g. "* *") — strip delimiters entirely.
# Require at least one whitespace char so that literal ** or ~~ in passthrough
# text is not mistakenly consumed as an empty span.
_XEP0393_EMPTY_SPAN_RE = re.compile(r"([*_~`])([ \t]+)(\1)")


def _fix_xep0393_whitespace(text: str) -> str:
    """Move leading/trailing whitespace outside XEP-0393 span delimiters."""
    # First strip spans that contain only whitespace (no valid content)
    text = _XEP0393_EMPTY_SPAN_RE.sub(r"\2", text)
    # Then move leading/trailing whitespace outside remaining spans
    prev = None
    while prev != text:
        prev = text
        text = _XEP0393_WS_FIX_RE.sub(r"\2\1\3\1\4", text)
    return text
