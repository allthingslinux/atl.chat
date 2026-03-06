"""Shared types, regex patterns, and utilities for cross-protocol formatting.

This module is the single source of truth for:
- Style Flag enum and IR dataclasses (Span, CodeBlock, FormattedText)
- Shared regex patterns (URL_RE, FENCE_RE, ZWS_RE)
- IRC casefold utility for correct nick/channel comparison
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Flag, auto

# ---------------------------------------------------------------------------
# Style enum and IR dataclasses
# ---------------------------------------------------------------------------


class Style(Flag):
    """Formatting styles supported by the intermediate representation.

    SPOILER is intentionally absent — XEP-0382 (Spoiler Messages) is a
    message-level stanza in XMPP, not inline formatting.  Spoiler handling
    is a separate Pipeline step (unwrap_spoiler / wrap_spoiler) that sets
    a flag on TransformContext rather than encoding it in the IR.  This
    keeps the IR protocol-agnostic: Discord uses inline ||markers||, IRC
    uses fg==bg color codes, and XMPP uses a stanza-level element.
    """

    BOLD = auto()
    ITALIC = auto()
    UNDERLINE = auto()
    STRIKETHROUGH = auto()
    MONOSPACE = auto()


@dataclass
class Span:
    """A formatting span over a character range in plain text."""

    start: int
    end: int
    style: Style


@dataclass
class CodeBlock:
    """Fenced code block extracted from content."""

    language: str | None  # Language hint (e.g. "python"), None if unspecified
    content: str  # Raw code content (no fence markers)
    start: int  # Start offset in original content
    end: int  # End offset in original content


@dataclass
class FormattedText:
    """Protocol-agnostic intermediate representation."""

    plain: str  # Plain text content (no formatting markers)
    spans: list[Span] = field(default_factory=list)  # Non-overlapping formatting spans
    code_blocks: list[CodeBlock] = field(default_factory=list)  # Fenced code blocks


# ---------------------------------------------------------------------------
# Shared regex patterns (single source of truth)
# ---------------------------------------------------------------------------

URL_RE = re.compile(
    r"https?://[^\s<>\[\]()]+(?:\([^\s<>\[\]()]*\)|[^\s<>\[\]()])*",
    re.IGNORECASE,
)

FENCE_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)

ZWS_RE = re.compile(r"\u200B")


# ---------------------------------------------------------------------------
# IRC casefold
# ---------------------------------------------------------------------------

# rfc1459 folds uppercase → lowercase: [ → {, ] → }, \ → |, ~ → ^
# These extra mappings exist because IRC predates ASCII standardization;
# the characters []\ occupy codepoints that some national character sets
# used for accented letters, so the IRC spec treats them as case-equivalent.
_RFC1459_TABLE = str.maketrans("[]\\~", "{}|^")

# rfc1459-strict is the same but WITHOUT ~ → ^
_RFC1459_STRICT_TABLE = str.maketrans("[]\\", "{}|")


def irc_casefold(name: str, mapping: str = "rfc1459") -> str:
    """Case-fold *name* according to the IRC server's CASEMAPPING.

    Parameters
    ----------
    name:
        The nick or channel name to fold.
    mapping:
        One of ``"ascii"``, ``"rfc1459"`` (default), or
        ``"rfc1459-strict"``.

    Returns
    -------
    str
        The case-folded string.  The operation is idempotent:
        ``irc_casefold(irc_casefold(s, m), m) == irc_casefold(s, m)``.

    Notes
    -----
    pydle's ``normalize()`` has the rfc1459 replacement **backwards**
    (lowercase → uppercase).  This implementation follows the correct
    direction as confirmed by ergo's source: uppercase → lowercase.
    """
    if mapping == "ascii":
        return name.lower()

    # .lower() handles A-Z → a-z; the translate table handles the extras.
    lowered = name.lower()

    if mapping == "rfc1459":
        return lowered.translate(_RFC1459_TABLE)

    if mapping == "rfc1459-strict":
        return lowered.translate(_RFC1459_STRICT_TABLE)

    msg = f"unknown casemapping: {mapping!r}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Invalid XML character stripping
# ---------------------------------------------------------------------------

# XML 1.0 valid chars: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
# Everything else is invalid. We match the *invalid* set and remove it.
_INVALID_XML_RE = re.compile(
    "["
    "\x00-\x08"  # C0 controls before tab
    "\x0b"  # vertical tab
    "\x0c"  # form feed
    "\x0e-\x1f"  # C0 controls after CR
    "\ud800-\udfff"  # surrogates (can't appear in valid Python str, but be safe)
    "\ufffe\uffff"  # BOM-related noncharacters
    "]"
)


def strip_invalid_xml_chars(text: str) -> str:
    """Remove characters that are invalid in XML 1.0.

    Keeps tab (``\\x09``), line feed (``\\x0A``), and carriage return
    (``\\x0D``).  Strips all other ASCII control characters (``\\x00``–
    ``\\x08``, ``\\x0B``, ``\\x0C``, ``\\x0E``–``\\x1F``), surrogates,
    and ``U+FFFE`` / ``U+FFFF``.
    """
    return _INVALID_XML_RE.sub("", text)
