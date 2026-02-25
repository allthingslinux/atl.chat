"""Event bus — central dispatcher for adapter events (AUDIT §1)."""

from bridge.core.events import Dispatcher, EventTarget

__all__ = ["Bus", "EventTarget"]


class Bus:
    """Event bus wrapping the central dispatcher. Adapters register and receive events."""

    def __init__(self) -> None:
        self._dispatcher = Dispatcher()

    def register(self, target: EventTarget) -> None:
        """Register an adapter as event target."""
        self._dispatcher.register(target)

    def unregister(self, target: EventTarget) -> None:
        """Unregister an adapter."""
        self._dispatcher.unregister(target)

    @property
    def _adapters(self) -> list[EventTarget]:
        """Registered adapters (for adapter discovery)."""
        return self._dispatcher._targets

    def publish(self, source: str, evt: object) -> None:
        """Publish event to all targets that accept it."""
        self._dispatcher.dispatch(source, evt)
