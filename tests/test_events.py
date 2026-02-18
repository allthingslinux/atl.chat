"""Tests for event types and dispatcher."""

from __future__ import annotations

from bridge.events import (
    ConfigReload,
    Dispatcher,
    Join,
    MessageIn,
    MessageOut,
    Part,
    Quit,
)


class TargetCollector:
    """Event target that collects accepted events."""

    def __init__(self, accept_types: set[type]) -> None:
        self.events: list[tuple[str, object]] = []
        self._accept_types = accept_types

    def accept_event(self, source: str, evt: object) -> bool:
        return type(evt) in self._accept_types

    def push_event(self, source: str, evt: object) -> None:
        self.events.append((source, evt))


def test_dispatcher_forwards_to_accepting_targets() -> None:
    """Targets that accept an event receive it."""
    dispatcher = Dispatcher()
    collector = TargetCollector({MessageIn})

    dispatcher.register(collector)
    dispatcher.dispatch(
        "test",
        MessageIn(
            origin="discord",
            channel_id="c1",
            author_id="u1",
            author_display="Alice",
            content="hi",
            message_id="m1",
        ),
    )
    dispatcher.dispatch(
        "test",
        ConfigReload(),
    )

    assert len(collector.events) == 1
    source, evt = collector.events[0]
    assert source == "test"
    assert isinstance(evt, MessageIn)
    assert evt.content == "hi"


def test_dispatcher_ignores_non_accepting_targets() -> None:
    """Targets that don't accept an event don't receive it."""
    dispatcher = Dispatcher()
    collector = TargetCollector({MessageOut})  # Only wants MessageOut

    dispatcher.register(collector)
    dispatcher.dispatch(
        "test",
        MessageIn(
            origin="discord",
            channel_id="c1",
            author_id="u1",
            author_display="Alice",
            content="hi",
            message_id="m1",
        ),
    )

    assert len(collector.events) == 0


def test_event_factories() -> None:
    """Event factory functions return (type_name, evt) with correct evt types."""
    from bridge.events import config_reload, join, message_in, part, quit

    type_name, evt = message_in(
        origin="irc",
        channel_id="c1",
        author_id="u1",
        author_display="Bob",
        content="hello",
        message_id="m1",
    )
    assert type_name == "message_in"
    assert isinstance(evt, MessageIn)
    assert evt.origin == "irc"

    _, evt2 = join("irc", "c1", "u1", "Bob")
    assert isinstance(evt2, Join)

    _, evt3 = part("irc", "c1", "u1", "Bob", reason="bye")
    assert isinstance(evt3, Part)
    assert evt3.reason == "bye"

    _, evt4 = quit("irc", "u1", "Bob")
    assert isinstance(evt4, Quit)

    _, evt5 = config_reload()
    assert isinstance(evt5, ConfigReload)


def test_dispatcher_unregister() -> None:
    """Unregistered targets stop receiving events."""
    dispatcher = Dispatcher()
    collector = TargetCollector({MessageIn})

    dispatcher.register(collector)
    dispatcher.dispatch("test", MessageIn("d", "c", "u", "A", "hi", "m1"))
    assert len(collector.events) == 1

    dispatcher.unregister(collector)
    dispatcher.dispatch("test", MessageIn("d", "c", "u", "A", "hi2", "m2"))
    assert len(collector.events) == 1
