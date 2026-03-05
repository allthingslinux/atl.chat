"""Split long messages for IRC (512 byte limit) at word boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Matches fenced code blocks: ```[lang]\n...\n``` (multiline)
# Lang is optional and only recognized when followed by a newline (Discord convention).
# Inline fences (no newline after opener) have no lang — full content between fences.
_FENCED_CODE_RE = re.compile(r"```(\w+)?\n(.*?)```|```(.*?)```", re.DOTALL)


@dataclass
class CodeBlock:
    lang: str
    content: str


@dataclass
class ProcessedContent:
    """Content with code blocks extracted and replaced by placeholders."""

    text: str  # message text with code blocks replaced by {PASTE_N} tokens
    blocks: list[CodeBlock] = field(default_factory=list)  # extracted blocks in order


def extract_code_blocks(content: str) -> ProcessedContent:
    """Extract fenced code blocks from content, replacing each with a {PASTE_N} token.

    Returns ProcessedContent with the cleaned text and the list of extracted blocks.
    If there are no code blocks, .blocks is empty and .text == content.
    """
    blocks: list[CodeBlock] = []

    def _replace(m: re.Match) -> str:
        if m.group(3) is not None:
            # Inline fence: ```content``` (no newline after opener)
            lang = ""
            body = m.group(3)
        else:
            # Block fence: ```[lang]\ncontent```
            lang = (m.group(1) or "").strip()
            body = m.group(2)
        # Strip a single trailing newline from block content (artifact of the closing ```)
        if body.endswith("\n"):
            body = body[:-1]
        blocks.append(CodeBlock(lang=lang, content=body))
        return f"{{PASTE_{len(blocks) - 1}}}"

    text = _FENCED_CODE_RE.sub(_replace, content)
    return ProcessedContent(text=text, blocks=blocks)


def split_irc_lines(content: str, max_bytes: int = 450) -> list[str]:
    """Split content on newlines first, then byte-split each line.

    This preserves multi-line Discord messages as separate IRC messages
    rather than collapsing them into a single mangled line.
    Empty lines are skipped — blank-only messages are noise on IRC.
    """
    lines = content.splitlines() or [""]
    result: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        result.extend(split_irc_message(line, max_bytes=max_bytes))
    return result or [""]


def split_irc_message(content: str, max_bytes: int = 450) -> list[str]:
    """Split content into chunks at word boundaries, each <= max_bytes.

    IRC messages are limited to 512 bytes total (prefix + PRIVMSG + target + content + CRLF).
    We use 450 to leave room for "PRIVMSG #channel :" and tags overhead.
    Never splits in the middle of a UTF-8 multi-byte character.
    """
    if not content:
        return []
    encoded = content.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return [content]

    chunks: list[str] = []
    start = 0
    while start < len(encoded):
        end = min(start + max_bytes, len(encoded))
        chunk_bytes = encoded[start:end]
        # Avoid splitting mid-UTF8: back up to a valid character boundary
        while chunk_bytes:
            try:
                chunk_bytes.decode("utf-8", errors="strict")
                break
            except UnicodeDecodeError:
                chunk_bytes = chunk_bytes[:-1]
        if not chunk_bytes:
            # Invalid UTF-8 at start; take one byte (decode will replace)
            chunk_bytes = encoded[start : start + 1]
            end = start + 1
        else:
            end = start + len(chunk_bytes)
        # Try to break at word boundary (space, newline)
        if end < len(encoded):
            last_space = chunk_bytes.rfind(b" ")
            if last_space > max_bytes // 2:
                new_chunk = encoded[start : start + last_space + 1]
                while new_chunk:
                    try:
                        new_chunk.decode("utf-8", errors="strict")
                        chunk_bytes = new_chunk
                        end = start + len(chunk_bytes)
                        break
                    except UnicodeDecodeError:
                        new_chunk = new_chunk[:-1]
        chunk = chunk_bytes.decode("utf-8", errors="replace")
        chunks.append(chunk)
        start = end
    return chunks
