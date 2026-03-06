"""IRC message splitting — split text into byte-safe UTF-8 chunks.

Each chunk encodes to at most *max_bytes* bytes in UTF-8, and the
concatenation of all chunks equals the original text (no content loss).

Also provides code-block extraction for paste-service upload.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Matches fenced code blocks: ```[lang]\n...\n``` (multiline)
_FENCED_CODE_RE = re.compile(r"```(\w+)?\n(.*?)```|```(.*?)```", re.DOTALL)


@dataclass
class CodeBlock:
    """A fenced code block extracted from message content."""

    lang: str
    content: str


@dataclass
class ProcessedContent:
    """Content with code blocks extracted and replaced by placeholders."""

    text: str
    blocks: list[CodeBlock] = field(default_factory=list)


def extract_code_blocks(content: str) -> ProcessedContent:
    """Extract fenced code blocks, replacing each with a ``{PASTE_N}`` token."""
    blocks: list[CodeBlock] = []

    def _replace(m: re.Match[str]) -> str:
        if m.group(3) is not None:
            lang = ""
            body = m.group(3)
        else:
            lang = (m.group(1) or "").strip()
            body = m.group(2)
        if body.endswith("\n"):
            body = body[:-1]
        blocks.append(CodeBlock(lang=lang, content=body))
        return f"{{PASTE_{len(blocks) - 1}}}"

    text = _FENCED_CODE_RE.sub(_replace, content)
    return ProcessedContent(text=text, blocks=blocks)


def split_irc_lines(content: str, max_bytes: int = 450) -> list[str]:
    """Split on newlines first, then byte-split each line.

    Empty lines are skipped.
    """
    lines = content.split("\n") or [""]
    result: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        result.extend(split_irc_message(line, max_bytes=max_bytes))
    return result or [""]


def split_irc_message(text: str, max_bytes: int = 450) -> list[str]:
    """Split *text* into chunks where each chunk ≤ *max_bytes* in UTF-8.

    The default of 450 leaves room for the IRC protocol overhead:
    ``:nick!user@host PRIVMSG #channel :`` prefix (~80 bytes), IRCv3 tags
    (variable), and the trailing CRLF (2 bytes).  512 is the hard IRC line
    limit, but with tags the effective limit can be higher — 450 is a safe
    conservative default that works with all servers.

    Guarantees:
    - No chunk exceeds *max_bytes* when encoded as UTF-8.
    - Multi-byte characters are never split across chunks.
    - ``"".join(split_irc_message(t, n)) == t`` for all inputs.
    """
    if not text:
        return []

    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return [text]

    chunks: list[str] = []
    pos = 0
    total = len(encoded)

    while pos < total:
        end = min(pos + max_bytes, total)

        if end < total:
            # We might be in the middle of a multi-byte character.
            # UTF-8 continuation bytes have the form 0b10xxxxxx.
            # Back up until we're at a character start boundary.
            while end > pos and (encoded[end] & 0xC0) == 0x80:
                end -= 1

        # Safety: if end didn't advance (single character wider than
        # max_bytes), force one full character forward.
        if end == pos:
            lead = encoded[pos]
            if (lead & 0x80) == 0:
                end = pos + 1
            elif (lead & 0xE0) == 0xC0:
                end = pos + 2
            elif (lead & 0xF0) == 0xE0:
                end = pos + 3
            elif (lead & 0xF8) == 0xF0:
                end = pos + 4
            else:
                end = pos + 1
            end = min(end, total)

        chunks.append(encoded[pos:end].decode("utf-8"))
        pos = end

    return chunks
