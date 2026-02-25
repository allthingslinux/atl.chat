"""Resolve @nick in IRC/XMPP content to Discord user mention for cross-protocol pings."""

from __future__ import annotations

import re

import discord

# Match @identifier — capture after @ until whitespace, @, or #
_AT_PATTERN = re.compile(r"@([^\s@#]+)")
# Do not resolve these
_SKIP_IDENTIFIERS = frozenset({"everyone", "here"})


def _match_member(member: discord.Member, identifier: str) -> bool:
    """Case-insensitive match: nick, display_name, or name."""
    ident = identifier.lower()
    return bool(
        (member.nick is not None and member.nick.lower() == ident)
        or (member.display_name and member.display_name.lower() == ident)
        or (member.name and member.name.lower() == ident)
    )


def _resolve_identifier(guild: discord.Guild, identifier: str) -> discord.Member | None:
    """Find guild member by identifier (nick, display_name, or name). Returns None if not found."""
    if identifier.lower() in _SKIP_IDENTIFIERS:
        return None
    return discord.utils.find(lambda m: _match_member(m, identifier), guild.members)


def _resolve_in_text(text: str, guild: discord.Guild) -> str:
    """Replace @identifier with <@userId> when member is found. Skip inside backticks."""
    result_parts: list[str] = []
    i = 0
    while i < len(text):
        # Skip code blocks: ```...``` or `...` — do not resolve inside
        if text[i] == "`":
            backtick_start = i
            i += 1
            # Triple backtick (code block)
            if i + 1 < len(text) and text[i : i + 2] == "``":
                i += 2
                while i + 2 < len(text):
                    if text[i : i + 3] == "```":
                        i += 3
                        break
                    i += 1
            else:
                # Single backtick (inline code)
                while i < len(text) and text[i] != "`":
                    i += 1
                if i < len(text):
                    i += 1
            result_parts.append(text[backtick_start:i])
            continue
        # Look for @identifier
        match = _AT_PATTERN.match(text[i:])
        if match:
            identifier = match.group(1)
            member = _resolve_identifier(guild, identifier)
            if member:
                result_parts.append(f"<@{member.id}>")
            else:
                result_parts.append(match.group(0))
            i += match.end()
            continue
        result_parts.append(text[i])
        i += 1
    return "".join(result_parts)


def resolve_mentions(content: str, guild: discord.Guild | None) -> str:
    """Resolve @nick in content to Discord <@userId> when guild has matching member.

    Skips @everyone and @here. Does not resolve inside backticks.
    Returns content unchanged if guild is None.
    """
    if not guild or not content:
        return content
    return _resolve_in_text(content, guild)
