"""Strip XEP-0461 / Matrix reply fallback from content when bridging replies."""


def add_reply_fallback(content: str, quoted: str, *, author: str | None = None) -> str:
    """Format reply for IRC: nick: > quoted | reply (IRC forbids newlines, so single line)."""
    quoted_clean = quoted.strip()
    if not quoted_clean:
        return content
    # Normalize: ensure quoted has > prefix, collapse newlines to space for IRC
    if not quoted_clean.startswith(">"):
        quoted_clean = "> " + quoted_clean
    quoted_line = " ".join(quoted_clean.splitlines())
    reply_part = f"{quoted_line} | {content}"
    if author:
        return f"{author}: {reply_part}"
    return reply_part


def strip_reply_fallback(content: str) -> str:
    """Remove leading lines with '> ' or '>' prefix (XEP-0461/Matrix reply fallback).

    When we show reply context via link button or IRC reply tag, we should not
    also include the quoted block in the message body.
    """
    lines = content.splitlines()
    out: list[str] = []
    for line in lines:
        s = line.lstrip()
        if s.startswith(">") and (len(s) == 1 or s[1] in (" ", "\t")):
            continue
        out.append(line)
    return "\n".join(out).strip()
