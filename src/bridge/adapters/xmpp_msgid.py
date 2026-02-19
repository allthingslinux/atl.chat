"""XMPP message ID tracking with TTL cache for edit correlation."""

from __future__ import annotations

import time
from typing import NamedTuple


class XMPPMessageMapping(NamedTuple):
    """Maps XMPP stanza ID to Discord message ID and vice versa."""

    xmpp_id: str
    discord_id: str
    room_jid: str
    timestamp: float


class XMPPMessageIDTracker:
    """Track XMPP message ID <-> Discord message ID mappings with TTL."""

    def __init__(self, ttl_seconds: int = 3600):
        self._ttl = ttl_seconds
        self._xmpp_to_discord: dict[str, XMPPMessageMapping] = {}
        self._discord_to_xmpp: dict[str, XMPPMessageMapping] = {}

    def store(self, xmpp_id: str, discord_id: str, room_jid: str):
        """Store bidirectional mapping."""
        mapping = XMPPMessageMapping(
            xmpp_id=xmpp_id,
            discord_id=discord_id,
            room_jid=room_jid,
            timestamp=time.time(),
        )
        self._xmpp_to_discord[xmpp_id] = mapping
        self._discord_to_xmpp[discord_id] = mapping

    def get_discord_id(self, xmpp_id: str) -> str | None:
        """Get Discord message ID from XMPP message ID."""
        self._cleanup()
        mapping = self._xmpp_to_discord.get(xmpp_id)
        return mapping.discord_id if mapping else None

    def get_xmpp_id(self, discord_id: str) -> str | None:
        """Get XMPP message ID from Discord message ID."""
        self._cleanup()
        mapping = self._discord_to_xmpp.get(discord_id)
        return mapping.xmpp_id if mapping else None

    def get_room_jid(self, discord_id: str) -> str | None:
        """Get room JID from Discord message ID."""
        self._cleanup()
        mapping = self._discord_to_xmpp.get(discord_id)
        return mapping.room_jid if mapping else None

    def _cleanup(self):
        """Remove expired entries."""
        now = time.time()
        cutoff = now - self._ttl

        # Clean XMPP -> Discord
        expired_xmpp = [
            xmpp_id
            for xmpp_id, mapping in self._xmpp_to_discord.items()
            if mapping.timestamp < cutoff
        ]
        for xmpp_id in expired_xmpp:
            del self._xmpp_to_discord[xmpp_id]

        # Clean Discord -> XMPP
        expired_discord = [
            discord_id
            for discord_id, mapping in self._discord_to_xmpp.items()
            if mapping.timestamp < cutoff
        ]
        for discord_id in expired_discord:
            del self._discord_to_xmpp[discord_id]
