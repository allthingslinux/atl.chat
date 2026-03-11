"""MessageIDResolver: port for cross-protocol message ID resolution (AUDIT §3.1)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from cachetools import TTLCache

from bridge.adapters.irc.msgid import MessageIDTracker

if TYPE_CHECKING:
    from bridge.adapters.xmpp.component import XMPPComponent


class MessageIDResolver(Protocol):
    """Resolve message IDs across protocols (IRC/XMPP <-> Discord)."""

    def get_discord_id(self, source: str, source_id: str) -> str | None:
        """Resolve source protocol message ID to Discord message ID."""
        ...

    def store_irc(self, irc_msgid: str, discord_id: str) -> None:
        """Store IRC msgid -> Discord ID mapping."""
        ...

    def store_xmpp(self, xmpp_id: str, discord_id: str, muc_jid: str) -> None:
        """Store XMPP message ID -> Discord ID mapping."""
        ...

    def add_xmpp_alias(self, alias: str, xmpp_id: str) -> bool:
        """Add alias for XMPP message ID lookups."""
        ...

    def add_discord_id_alias(self, discord_id: str, irc_msgid: str) -> bool:
        """Link Discord ID to IRC msgid for XMPP reply resolution."""
        ...

    def add_irc_discord_id_alias(self, new_discord_id: str, existing_value: str) -> bool:
        """Link Discord ID to IRC msgid for IRC reaction routing (XMPP-origin messages)."""
        ...

    def get_xmpp_component(self) -> XMPPComponent | None:
        """Get XMPP component for file uploads (attachments)."""
        ...

    def register_irc(self, tracker: MessageIDTracker) -> None:
        """Register IRC message ID tracker (called by IRCAdapter)."""
        ...

    def register_xmpp(self, component: XMPPComponent) -> None:
        """Register XMPP component (called by XMPPAdapter)."""
        ...

    def store_irc_xmpp_pending(self, irc_msgid: str, xmpp_id: str, muc_jid: str) -> None:
        """Store pending irc_msgid → xmpp_id mapping for later Discord ID resolution."""
        ...

    def resolve_irc_xmpp_pending(self, irc_msgid: str, discord_id: str) -> bool:
        """Resolve pending mapping: store xmpp_id → discord_id using stored irc_msgid → xmpp_id."""
        ...


class DefaultMessageIDResolver:
    """Implementation that delegates to IRC and XMPP trackers."""

    def __init__(self) -> None:
        self._irc_tracker: MessageIDTracker | None = None
        self._xmpp_component: XMPPComponent | None = None
        # Pending irc_msgid → (xmpp_id, muc_jid) for IRC-origin messages relayed to XMPP.
        # Resolved when the Discord adapter gets the webhook discord_id.
        # TTLCache prevents unbounded growth if the Discord webhook never fires.
        self._irc_xmpp_pending: TTLCache[str, tuple[str, str]] = TTLCache(maxsize=2000, ttl=3600)

    def register_irc(self, tracker: MessageIDTracker) -> None:
        """Register IRC message ID tracker (called by IRCAdapter)."""
        self._irc_tracker = tracker

    def register_xmpp(self, component: XMPPComponent) -> None:
        """Register XMPP component (called by XMPPAdapter when component is created)."""
        self._xmpp_component = component

    def get_discord_id(self, source: str, source_id: str) -> str | None:
        if source == "irc" and self._irc_tracker:
            return self._irc_tracker.get_discord_id(source_id)
        if source == "xmpp" and self._xmpp_component:
            return self._xmpp_component._msgid_tracker.get_discord_id(source_id)
        return None

    def store_irc(self, irc_msgid: str, discord_id: str) -> None:
        if self._irc_tracker:
            self._irc_tracker.store(irc_msgid, discord_id)

    def store_xmpp(self, xmpp_id: str, discord_id: str, muc_jid: str) -> None:
        if self._xmpp_component:
            self._xmpp_component._msgid_tracker.store(xmpp_id, discord_id, muc_jid)

    def add_xmpp_alias(self, alias: str, xmpp_id: str) -> bool:
        if self._xmpp_component:
            return self._xmpp_component._msgid_tracker.add_alias(alias, xmpp_id)
        return False

    def add_discord_id_alias(self, discord_id: str, irc_msgid: str) -> bool:
        if self._xmpp_component:
            return self._xmpp_component._msgid_tracker.add_discord_id_alias(discord_id, irc_msgid)
        return False

    def add_irc_discord_id_alias(self, new_discord_id: str, existing_value: str) -> bool:
        """Add Discord ID alias to IRC tracker so get_irc_msgid(discord_id) works for XMPP-origin."""
        if self._irc_tracker:
            return self._irc_tracker.add_discord_id_alias(new_discord_id, existing_value)
        return False

    def get_xmpp_component(self) -> XMPPComponent | None:
        return self._xmpp_component

    def store_irc_xmpp_pending(self, irc_msgid: str, xmpp_id: str, muc_jid: str) -> None:
        """Store pending irc_msgid → (xmpp_id, muc_jid) for later resolution.

        This handles the IRC→Discord→XMPP message ID chain:
        1. IRC message arrives with irc_msgid, gets relayed to XMPP with xmpp_id.
        2. The XMPP adapter sends the message and stores (xmpp_id, irc_msgid) in
           its tracker so the MUC echo can capture the stanza-id.
        3. When the Discord webhook returns the real discord_id, we call
           resolve_irc_xmpp_pending to replace irc_msgid with discord_id in the
           XMPP tracker, enabling reactions on IRC-originated messages.

        Without this pre-registration, the MUC echo fires before any mapping
        exists, and the stanza-id is silently lost — causing reactions on
        IRC-originated messages to target the origin-id instead of the
        stanza-id (Gajim/Dino ignore those).
        """
        self._irc_xmpp_pending[irc_msgid] = (xmpp_id, muc_jid)
        if self._xmpp_component:
            self._xmpp_component._msgid_tracker.store(xmpp_id, irc_msgid, muc_jid)

    def resolve_irc_xmpp_pending(self, irc_msgid: str, discord_id: str) -> bool:
        """Resolve pending mapping: update xmpp_id (and aliases like stanza-id) → discord_id.

        Uses update_discord_id so stanza_id alias (added by echo) also returns the real
        discord_id — Fluux reactions target stanza-id, so get_discord_id must resolve it.
        """
        pending = self._irc_xmpp_pending.pop(irc_msgid, None)
        if not pending:
            return False
        xmpp_id, _ = pending
        if self._xmpp_component:
            return self._xmpp_component._msgid_tracker.update_discord_id(xmpp_id, discord_id)
        return False
