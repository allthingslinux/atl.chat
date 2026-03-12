"""Abstract base class for cross-protocol identity resolution (Design §2.4 D3)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class IdentityResolver(ABC):
    """Abstract base for identity resolution across protocols.

    Implementations:
        - ``PortalIdentityResolver`` (production, backed by Portal API)
        - ``DevIdentityResolver`` (testing, in-memory mappings)
    """

    # -- Discord lookups -----------------------------------------------------

    @abstractmethod
    async def discord_to_irc(self, discord_id: str) -> str | None:
        """Resolve a Discord user ID to an IRC nick, or ``None``."""
        ...

    @abstractmethod
    async def discord_to_xmpp(self, discord_id: str) -> str | None:
        """Resolve a Discord user ID to an XMPP JID, or ``None``."""
        ...

    @abstractmethod
    async def discord_to_portal_user(self, discord_id: str) -> str | None:
        """Resolve a Discord user ID to a Portal user ID, or ``None``."""
        ...

    # -- IRC lookups ---------------------------------------------------------

    @abstractmethod
    async def irc_to_discord(self, nick: str, server: str | None = None) -> str | None:
        """Resolve an IRC nick to a Discord user ID, or ``None``."""
        ...

    @abstractmethod
    async def irc_to_xmpp(self, nick: str, server: str | None = None) -> str | None:
        """Resolve an IRC nick to an XMPP JID, or ``None``."""
        ...

    @abstractmethod
    async def irc_to_portal_user(self, nick: str, server: str | None = None) -> str | None:
        """Resolve an IRC nick to a Portal user ID, or ``None``."""
        ...

    # -- XMPP lookups --------------------------------------------------------

    @abstractmethod
    async def xmpp_to_discord(self, jid: str) -> str | None:
        """Resolve an XMPP JID to a Discord user ID, or ``None``."""
        ...

    @abstractmethod
    async def xmpp_to_irc(self, jid: str) -> str | None:
        """Resolve an XMPP JID to an IRC nick, or ``None``."""
        ...

    @abstractmethod
    async def xmpp_to_portal_user(self, jid: str) -> str | None:
        """Resolve an XMPP JID to a Portal user ID, or ``None``."""
        ...

    # -- Capability checks ---------------------------------------------------

    @abstractmethod
    async def has_irc(self, discord_id: str) -> bool:
        """Return ``True`` if the Discord user has a linked IRC identity."""
        ...

    @abstractmethod
    async def has_xmpp(self, discord_id: str) -> bool:
        """Return ``True`` if the Discord user has a linked XMPP identity."""
        ...

    # -- Avatar (Portal user.image) -------------------------------------------

    @abstractmethod
    async def avatar_for_discord(self, discord_id: str) -> str | None:
        """Return avatar URL for Discord user (from Portal), or ``None``."""
        ...

    @abstractmethod
    async def avatar_for_irc(self, nick: str, server: str | None = None) -> str | None:
        """Return avatar URL for IRC nick (from Portal), or ``None``."""
        ...

    @abstractmethod
    async def avatar_for_xmpp(self, jid: str) -> str | None:
        """Return avatar URL for XMPP JID (from Portal), or ``None``."""
        ...
