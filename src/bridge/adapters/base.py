"""Base adapter interface (AUDIT §1: subscribe/publish, start/stop)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class AdapterBase(ABC):
    """Interface for protocol adapters. Subscribe to bus, publish events, start/stop."""

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
