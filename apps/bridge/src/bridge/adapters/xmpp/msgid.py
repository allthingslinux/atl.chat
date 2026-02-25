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
        self._discord_to_stanza_id: dict[str, str] = {}  # discord_id -> stanza_id (for reactions)

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

    def add_stanza_id_alias(self, our_id: str, stanza_id: str) -> bool:
        """Add stanza-id as alias for lookups (reactions use stanza-id; corrections use our_id)."""
        self._cleanup()
        mapping = self._xmpp_to_discord.get(our_id)
        if not mapping:
            return False
        self._xmpp_to_discord[stanza_id] = mapping
        self._discord_to_stanza_id[mapping.discord_id] = stanza_id
        return True

    def add_alias(self, alias_id: str, primary_xmpp_id: str) -> bool:
        """Add alias for get_discord_id lookups (e.g. origin-id when primary is stanza-id)."""
        self._cleanup()
        mapping = self._xmpp_to_discord.get(primary_xmpp_id)
        if not mapping:
            return False
        self._xmpp_to_discord[alias_id] = mapping
        return True

    def add_discord_id_alias(self, new_discord_id: str, existing_key: str) -> bool:
        """Add Discord ID as alias for get_xmpp_id lookups.

        Used when an IRC message is relayed: XMPP stores (xmpp_id, irc_msgid) and Discord
        later gets the real discord_id from the webhook. This links discord_id -> xmpp_id
        so Discord replies to IRC webhooks resolve to the correct XMPP message.
        Also propagates stanza_id so get_xmpp_id_for_reaction (used for replies) returns
        stanza-id for Gajim compatibility (clients match replies by stanza-id in MUC).
        """
        self._cleanup()
        mapping = self._discord_to_xmpp.get(existing_key)
        if not mapping:
            return False
        self._discord_to_xmpp[new_discord_id] = mapping
        stanza_id = self._discord_to_stanza_id.get(existing_key)
        if stanza_id:
            self._discord_to_stanza_id[new_discord_id] = stanza_id
        return True

    def get_discord_id(self, xmpp_id: str) -> str | None:
        """Get Discord message ID from XMPP message ID."""
        self._cleanup()
        mapping = self._xmpp_to_discord.get(xmpp_id)
        return mapping.discord_id if mapping else None

    def get_xmpp_id(self, discord_id: str) -> str | None:
        """Get XMPP message ID from Discord message ID (for corrections; uses our_id)."""
        self._cleanup()
        mapping = self._discord_to_xmpp.get(discord_id)
        return mapping.xmpp_id if mapping else None

    def get_xmpp_id_for_reaction(self, discord_id: str) -> str | None:
        """Get XMPP message ID for reaction targeting (prefers stanza-id when available)."""
        self._cleanup()
        stanza_id = self._discord_to_stanza_id.get(discord_id)
        if stanza_id:
            return stanza_id
        return self.get_xmpp_id(discord_id)

    def get_room_jid(self, discord_id: str) -> str | None:
        """Get room JID from Discord message ID."""
        self._cleanup()
        mapping = self._discord_to_xmpp.get(discord_id)
        return mapping.room_jid if mapping else None

    def update_xmpp_id(self, old_xmpp_id: str, new_xmpp_id: str) -> bool:
        """Replace old xmpp_id with new (e.g. MUC stanza-id) for existing mapping."""
        self._cleanup()
        mapping = self._xmpp_to_discord.pop(old_xmpp_id, None)
        if not mapping:
            return False
        new_mapping = XMPPMessageMapping(
            xmpp_id=new_xmpp_id,
            discord_id=mapping.discord_id,
            room_jid=mapping.room_jid,
            timestamp=mapping.timestamp,
        )
        self._xmpp_to_discord[new_xmpp_id] = new_mapping
        self._discord_to_xmpp[mapping.discord_id] = new_mapping
        return True

    def _cleanup(self):
        """Remove expired entries."""
        now = time.time()
        cutoff = now - self._ttl

        # Clean XMPP -> Discord
        expired_xmpp = [xmpp_id for xmpp_id, mapping in self._xmpp_to_discord.items() if mapping.timestamp < cutoff]
        for xmpp_id in expired_xmpp:
            del self._xmpp_to_discord[xmpp_id]

        # Clean Discord -> XMPP
        expired_discord = [
            discord_id for discord_id, mapping in self._discord_to_xmpp.items() if mapping.timestamp < cutoff
        ]
        for discord_id in expired_discord:
            del self._discord_to_xmpp[discord_id]
            self._discord_to_stanza_id.pop(discord_id, None)
