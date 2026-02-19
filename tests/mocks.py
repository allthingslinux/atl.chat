"""Mock adapters for testing bridge without real protocol connections."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from bridge.adapters.base import AdapterBase
from bridge.events import MessageIn, MessageOut, Join, Part


class MockAdapter(AdapterBase):
    """Mock adapter that captures events without real connections."""

    def __init__(self, name: str) -> None:
        self._name = name
        self.received_events: list[tuple[str, object]] = []
        self.sent_messages: list[MessageOut] = []
        self._running = False

    @property
    def name(self) -> str:
        return self._name

    def accept_event(self, source: str, evt: object) -> bool:
        """Accept MessageOut targeting this adapter."""
        if isinstance(evt, MessageOut) and evt.target_origin == self._name:
            return True
        return False

    def push_event(self, source: str, evt: object) -> None:
        """Capture event."""
        self.received_events.append((source, evt))
        if isinstance(evt, MessageOut):
            self.sent_messages.append(evt)

    async def start(self) -> None:
        """Mock start."""
        self._running = True

    async def stop(self) -> None:
        """Mock stop."""
        self._running = False

    def clear(self) -> None:
        """Clear captured events."""
        self.received_events.clear()
        self.sent_messages.clear()


class MockDiscordAdapter(MockAdapter):
    """Mock Discord adapter."""

    def __init__(self) -> None:
        super().__init__("discord")


class MockIRCAdapter(MockAdapter):
    """Mock IRC adapter."""

    def __init__(self) -> None:
        super().__init__("irc")


class MockXMPPAdapter(MockAdapter):
    """Mock XMPP adapter."""

    def __init__(self) -> None:
        super().__init__("xmpp")
