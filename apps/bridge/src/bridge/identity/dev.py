"""Dev-only identity resolver (AUDIT §2.H)."""

from __future__ import annotations

import os
import re

_IRC_NICK_RE = re.compile(r"[^a-zA-Z0-9_\-\[\]\\`^{}|]")


def _sanitize_irc_nick(nick: str) -> str:
    """Sanitize string for use as IRC nick."""
    sanitized = _IRC_NICK_RE.sub("", nick)
    return (sanitized or "user")[:32]


class DevIdentityResolver:
    """Dev-only identity resolver for IRC puppets without Portal."""

    def __init__(self) -> None:
        raw = os.environ.get("BRIDGE_DEV_IRC_NICK_MAP", "").strip()
        self._nick_map: dict[str, str] = {}
        for pair in raw.split(",") if raw else []:
            part = pair.strip()
            if ":" in part:
                discord_id, nick = part.split(":", 1)
                discord_id = discord_id.strip()
                nick = _sanitize_irc_nick(nick.strip())
                if discord_id and nick:
                    self._nick_map[discord_id] = nick

    async def discord_to_irc(self, discord_id: str) -> str | None:
        if discord_id in self._nick_map:
            return self._nick_map[discord_id]
        suffix = discord_id[-8:] if len(discord_id) >= 8 else discord_id
        return f"atl_dev_{suffix}"

    async def has_irc(self, discord_id: str) -> bool:
        return True

    async def discord_to_xmpp(self, discord_id: str) -> str | None:
        return None

    async def discord_to_portal_user(self, discord_id: str) -> str | None:
        return None

    async def irc_to_xmpp(self, nick: str, server: str | None = None) -> str | None:
        return None

    async def irc_to_discord(self, nick: str, server: str | None = None) -> str | None:
        return next((did for did, n in self._nick_map.items() if n == nick), None)

    async def irc_to_portal_user(self, nick: str, server: str | None = None) -> str | None:
        return None

    async def xmpp_to_irc(self, jid: str) -> str | None:
        return None

    async def xmpp_to_discord(self, jid: str) -> str | None:
        return None

    async def xmpp_to_portal_user(self, jid: str) -> str | None:
        return None

    async def has_xmpp(self, discord_id: str) -> bool:
        return False
