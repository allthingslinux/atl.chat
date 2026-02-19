"""Split long messages for IRC (512 byte limit) at word boundaries."""

from __future__ import annotations


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
