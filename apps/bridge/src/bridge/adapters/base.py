"""Base adapter (AUDIT §3.2: thin wrapper implementing BridgeAdapter)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class AdapterBase(ABC):
    """Thin base for adapters. Implements BridgeAdapter with default accept_event/push_event."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Adapter identifier (e.g. 'discord', 'irc', 'xmpp')."""
        ...

    def accept_event(self, source: str, evt: object) -> bool:
        """Return True if this adapter wants the event. Override for filtering."""
        return False

    def push_event(self, source: str, evt: object) -> None:
        """Handle event. Override to process. May queue for async handling."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start the adapter (connect, register handlers)."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the adapter (disconnect, cleanup)."""
        ...
