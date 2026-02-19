"""Convert Discord markdown to plain text for IRC."""

from __future__ import annotations

import re

# URL pattern - do not modify content inside URLs
_URL_PATTERN = re.compile(
    r"https?://[^\s<>\[\]()]+(?:\([^\s<>\[\]()]*\)|[^\s<>\[\]()])*",
    re.IGNORECASE,
)


def discord_to_irc(content: str) -> str:
    """Strip Discord markdown to plain text. Preserves URLs."""
    if not content:
        return content

    # Split by URLs to preserve them
    parts: list[str] = []
    last_end = 0
    for m in _URL_PATTERN.finditer(content):
        if m.start() > last_end:
            parts.append(_strip_markdown(content[last_end : m.start()]))
        parts.append(m.group(0))
        last_end = m.end()
    if last_end < len(content):
        parts.append(_strip_markdown(content[last_end:]))
    return "".join(parts) if parts else _strip_markdown(content)


def _strip_markdown(text: str) -> str:
    """Remove Discord markdown from text."""
    # Spoilers ||text|| (require at least one char between pipes)
    text = re.sub(r"\|\|([^|]+)\|\|", r"\1", text)
    # Bold **text** or __text__
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    # Italic *text* or _text_ (single)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"\1", text)
    # Strikethrough ~~text~~
    text = re.sub(r"~~([^~]+)~~", r"\1", text)
    # Code block ```...``` and double backticks ``...`` before single `...`
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"``([^`]+)``", r"\1", text)
    # Inline code `text`
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text
