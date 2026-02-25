"""MessageIDResolver: port for cross-protocol message ID resolution (AUDIT §3.1)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

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

    def get_xmpp_component(self) -> XMPPComponent | None:
        """Get XMPP component for file uploads (attachments)."""
        ...

    def register_irc(self, tracker: MessageIDTracker) -> None:
        """Register IRC message ID tracker (called by IRCAdapter)."""
        ...

    def register_xmpp(self, component: XMPPComponent) -> None:
        """Register XMPP component (called by XMPPAdapter)."""
        ...


class DefaultMessageIDResolver:
    """Implementation that delegates to IRC and XMPP trackers."""

    def __init__(self) -> None:
        self._irc_tracker: MessageIDTracker | None = None
        self._xmpp_component: XMPPComponent | None = None

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

    def get_xmpp_component(self) -> XMPPComponent | None:
        return self._xmpp_component
