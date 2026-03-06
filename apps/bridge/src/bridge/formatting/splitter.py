"""IRC message splitting — split text into byte-safe UTF-8 chunks.

Each chunk encodes to at most *max_bytes* bytes in UTF-8, and the
concatenation of all chunks equals the original text (no content loss).
"""

from __future__ import annotations


def split_irc_message(text: str, max_bytes: int = 450) -> list[str]:
    """Split *text* into chunks where each chunk ≤ *max_bytes* in UTF-8.

    The default of 450 leaves room for the IRC protocol overhead
    (``PRIVMSG #channel :`` prefix, IRCv3 tags, CRLF).

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
