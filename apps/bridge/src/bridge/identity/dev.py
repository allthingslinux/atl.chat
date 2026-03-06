"""In-memory identity resolver for testing (Design §2.4 D3, Requirement 12.3)."""

from __future__ import annotations

import os
import re

from bridge.identity.base import IdentityResolver

_IRC_NICK_RE = re.compile(r"[^a-zA-Z0-9_\-\[\]\\`^{}|]")


def _sanitize_irc_nick(nick: str) -> str:
    """Sanitize string for use as IRC nick."""
    sanitized = _IRC_NICK_RE.sub("", nick)
    return (sanitized or "user")[:32]


class DevIdentityResolver(IdentityResolver):
    """In-memory identity resolver for testing without Portal.

    Extends the :class:`IdentityResolver` ABC with simple dict-backed
    storage.  Mappings can be seeded from the ``BRIDGE_DEV_IRC_NICK_MAP``
    environment variable (for backward compatibility) or added
    programmatically via the ``add_*`` helpers.
    """

    def __init__(self) -> None:
        # discord_id -> irc_nick
        self._discord_irc: dict[str, str] = {}
        # discord_id -> xmpp_jid
        self._discord_xmpp: dict[str, str] = {}
        # irc_nick -> xmpp_jid  (keyed by nick)
        self._irc_xmpp: dict[str, str] = {}
        # discord_id -> portal_user_id
        self._discord_portal: dict[str, str] = {}
        # irc_nick -> portal_user_id
        self._irc_portal: dict[str, str] = {}
        # xmpp_jid -> portal_user_id
        self._xmpp_portal: dict[str, str] = {}

        # Seed from env var for backward compatibility
        raw = os.environ.get("BRIDGE_DEV_IRC_NICK_MAP", "").strip()
        for pair in raw.split(",") if raw else []:
            part = pair.strip()
            if ":" in part:
                discord_id, nick = part.split(":", 1)
                discord_id = discord_id.strip()
                nick = _sanitize_irc_nick(nick.strip())
                if discord_id and nick:
                    self._discord_irc[discord_id] = nick

    # -- Programmatic mapping helpers ----------------------------------------

    def add_discord_irc_mapping(self, discord_id: str, irc_nick: str) -> None:
        """Register a Discord ↔ IRC identity mapping."""
        self._discord_irc[discord_id] = irc_nick

    def add_discord_xmpp_mapping(self, discord_id: str, xmpp_jid: str) -> None:
        """Register a Discord ↔ XMPP identity mapping."""
        self._discord_xmpp[discord_id] = xmpp_jid

    def add_irc_xmpp_mapping(self, irc_nick: str, xmpp_jid: str) -> None:
        """Register an IRC ↔ XMPP identity mapping."""
        self._irc_xmpp[irc_nick] = xmpp_jid

    def add_discord_portal_mapping(self, discord_id: str, portal_user_id: str) -> None:
        """Register a Discord → Portal user mapping."""
        self._discord_portal[discord_id] = portal_user_id

    def add_irc_portal_mapping(self, irc_nick: str, portal_user_id: str) -> None:
        """Register an IRC → Portal user mapping."""
        self._irc_portal[irc_nick] = portal_user_id

    def add_xmpp_portal_mapping(self, xmpp_jid: str, portal_user_id: str) -> None:
        """Register an XMPP → Portal user mapping."""
        self._xmpp_portal[xmpp_jid] = portal_user_id

    # -- IdentityResolver ABC implementation ---------------------------------

    async def discord_to_irc(self, discord_id: str) -> str | None:
        if discord_id in self._discord_irc:
            return self._discord_irc[discord_id]
        # Fallback: generate a dev nick from the Discord ID suffix
        suffix = discord_id[-8:] if len(discord_id) >= 8 else discord_id
        return f"atl_dev_{suffix}"

    async def discord_to_xmpp(self, discord_id: str) -> str | None:
        return self._discord_xmpp.get(discord_id)

    async def discord_to_portal_user(self, discord_id: str) -> str | None:
        return self._discord_portal.get(discord_id)

    async def irc_to_discord(self, nick: str, server: str | None = None) -> str | None:
        # Check explicit mappings first (reverse lookup)
        return next(
            (did for did, n in self._discord_irc.items() if n == nick),
            None,
        )

    async def irc_to_xmpp(self, nick: str, server: str | None = None) -> str | None:
        return self._irc_xmpp.get(nick)

    async def irc_to_portal_user(self, nick: str, server: str | None = None) -> str | None:
        return self._irc_portal.get(nick)

    async def xmpp_to_discord(self, jid: str) -> str | None:
        # Reverse lookup from discord_xmpp
        return next(
            (did for did, j in self._discord_xmpp.items() if j == jid),
            None,
        )

    async def xmpp_to_irc(self, jid: str) -> str | None:
        # Reverse lookup from irc_xmpp
        return next(
            (nick for nick, j in self._irc_xmpp.items() if j == jid),
            None,
        )

    async def xmpp_to_portal_user(self, jid: str) -> str | None:
        return self._xmpp_portal.get(jid)

    async def has_irc(self, discord_id: str) -> bool:
        return True

    async def has_xmpp(self, discord_id: str) -> bool:
        return discord_id in self._discord_xmpp
