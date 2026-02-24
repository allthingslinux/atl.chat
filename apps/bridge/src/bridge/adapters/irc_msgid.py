"""IRCv3 message ID tracking with TTL cache for edit/delete correlation."""

from __future__ import annotations

import time
from typing import NamedTuple


class MessageMapping(NamedTuple):
    """Maps IRC msgid to Discord message ID and vice versa."""

    irc_msgid: str
    discord_id: str
    timestamp: float


class MessageIDTracker:
    """Track IRC msgid <-> Discord message ID mappings with TTL."""

    def __init__(self, ttl_seconds: int = 3600):
        self._ttl = ttl_seconds
        self._irc_to_discord: dict[str, MessageMapping] = {}
        self._discord_to_irc: dict[str, MessageMapping] = {}

    def store(self, irc_msgid: str, discord_id: str):
        """Store bidirectional mapping."""
        mapping = MessageMapping(
            irc_msgid=irc_msgid,
            discord_id=discord_id,
            timestamp=time.time(),
        )
        self._irc_to_discord[irc_msgid] = mapping
        self._discord_to_irc[discord_id] = mapping

    def get_discord_id(self, irc_msgid: str) -> str | None:
        """Get Discord message ID from IRC msgid."""
        self._cleanup()
        mapping = self._irc_to_discord.get(irc_msgid)
        return mapping.discord_id if mapping else None

    def get_irc_msgid(self, discord_id: str) -> str | None:
        """Get IRC msgid from Discord message ID."""
        self._cleanup()
        mapping = self._discord_to_irc.get(discord_id)
        return mapping.irc_msgid if mapping else None

    def _cleanup(self):
        """Remove expired entries."""
        now = time.time()
        cutoff = now - self._ttl

        # Clean IRC -> Discord
        expired_irc = [
            msgid for msgid, mapping in self._irc_to_discord.items() if mapping.timestamp < cutoff
        ]
        for msgid in expired_irc:
            del self._irc_to_discord[msgid]

        # Clean Discord -> IRC
        expired_discord = [
            discord_id
            for discord_id, mapping in self._discord_to_irc.items()
            if mapping.timestamp < cutoff
        ]
        for discord_id in expired_discord:
            del self._discord_to_irc[discord_id]


class ReactionMapping(NamedTuple):
    """Maps (discord_id, emoji, author_id) to IRC reaction TAGMSG msgid for REDACT."""

    irc_reaction_msgid: str
    timestamp: float


class ReactionTracker:
    """Track reaction TAGMSG msgids for removal via REDACT. Key: (discord_id, emoji, author_id)."""

    def __init__(self, ttl_seconds: int = 3600):
        self._ttl = ttl_seconds
        self._key_to_msgid: dict[tuple[str, str, str], ReactionMapping] = {}
        self._msgid_to_key: dict[str, tuple[str, str, str]] = {}

    def store(self, discord_id: str, emoji: str, author_id: str, irc_reaction_msgid: str) -> None:
        """Store mapping for later REDACT on removal."""
        key = (discord_id, emoji, author_id)
        self._key_to_msgid[key] = ReactionMapping(
            irc_reaction_msgid=irc_reaction_msgid,
            timestamp=time.time(),
        )
        self._msgid_to_key[irc_reaction_msgid] = key

    def get_reaction_msgid(self, discord_id: str, emoji: str, author_id: str) -> str | None:
        """Get IRC msgid of our reaction TAGMSG for REDACT."""
        self._cleanup()
        key = (discord_id, emoji, author_id)
        mapping = self._key_to_msgid.get(key)
        return mapping.irc_reaction_msgid if mapping else None

    def get_reaction_key(self, irc_reaction_msgid: str) -> tuple[str, str, str] | None:
        """Get (discord_id, emoji, author_id) for IRC REDACT of reaction TAGMSG."""
        self._cleanup()
        return self._msgid_to_key.get(irc_reaction_msgid)

    def store_incoming(
        self, irc_reaction_msgid: str, discord_id: str, emoji: str, author_id: str
    ) -> None:
        """Store incoming IRC reaction TAGMSG for REDACT→removal mapping."""
        key = (discord_id, emoji, author_id)
        self._key_to_msgid[key] = ReactionMapping(
            irc_reaction_msgid=irc_reaction_msgid,
            timestamp=time.time(),
        )
        self._msgid_to_key[irc_reaction_msgid] = key

    def _cleanup(self) -> None:
        """Remove expired entries."""
        now = time.time()
        cutoff = now - self._ttl
        expired = [k for k, m in self._key_to_msgid.items() if m.timestamp < cutoff]
        for k in expired:
            m = self._key_to_msgid.pop(k, None)
            if m:
                self._msgid_to_key.pop(m.irc_reaction_msgid, None)
