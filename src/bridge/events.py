"""Event types and dispatcher (AUDIT §1: typed events, central dispatcher)."""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class MessageIn:
    """Inbound message event — protocol-agnostic."""

    origin: str  # "discord" | "irc" | "xmpp"
    channel_id: str
    author_id: str
    author_display: str
    content: str
    message_id: str
    reply_to_id: str | None = None
    is_edit: bool = False
    is_action: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageOut:
    """Outbound message event — to be sent to target protocol(s)."""

    target_origin: str  # "discord" | "irc" | "xmpp"
    channel_id: str
    author_id: str
    author_display: str
    content: str
    message_id: str
    reply_to_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Join:
    """User joined a channel."""

    origin: str
    channel_id: str
    user_id: str
    display: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Part:
    """User left a channel."""

    origin: str
    channel_id: str
    user_id: str
    display: str
    reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Quit:
    """User disconnected (IRC/XMPP)."""

    origin: str
    user_id: str
    display: str
    reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigReload:
    """Config was reloaded (e.g. SIGHUP)."""

    pass


class EventTarget(Protocol):
    """Adapter interface: accept_event + push_event (AUDIT §1)."""

    def accept_event(self, source: str, evt: object) -> bool:
        """Return True if this target wants the event."""
        ...

    def push_event(self, source: str, evt: object) -> None:
        """Handle the event (may be async via queue)."""
        ...


def event(type_name: str):
    """Decorator to mark a factory as producing an event with a given type."""

    def decorator(f: Any) -> Any:
        @functools.wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> tuple[str, object]:
            evt = f(*args, **kwargs)
            return (type_name, evt)

        wrapper.TYPE = type_name
        return wrapper

    return decorator


@event("message_in")
def message_in(
    origin: str,
    channel_id: str,
    author_id: str,
    author_display: str,
    content: str,
    message_id: str,
    *,
    reply_to_id: str | None = None,
    is_edit: bool = False,
    is_action: bool = False,
    raw: dict[str, Any] | None = None,
) -> MessageIn:
    return MessageIn(
        origin=origin,
        channel_id=channel_id,
        author_id=author_id,
        author_display=author_display,
        content=content,
        message_id=message_id,
        reply_to_id=reply_to_id,
        is_edit=is_edit,
        is_action=is_action,
        raw=raw or {},
    )


@event("message_out")
def message_out(
    target_origin: str,
    channel_id: str,
    author_id: str,
    author_display: str,
    content: str,
    message_id: str,
    *,
    reply_to_id: str | None = None,
    raw: dict[str, Any] | None = None,
) -> MessageOut:
    return MessageOut(
        target_origin=target_origin,
        channel_id=channel_id,
        author_id=author_id,
        author_display=author_display,
        content=content,
        message_id=message_id,
        reply_to_id=reply_to_id,
        raw=raw or {},
    )


@event("join")
def join(origin: str, channel_id: str, user_id: str, display: str) -> Join:
    return Join(origin=origin, channel_id=channel_id, user_id=user_id, display=display)


@event("part")
def part(
    origin: str,
    channel_id: str,
    user_id: str,
    display: str,
    *,
    reason: str | None = None,
) -> Part:
    return Part(
        origin=origin,
        channel_id=channel_id,
        user_id=user_id,
        display=display,
        reason=reason,
    )


@event("quit")
def quit(origin: str, user_id: str, display: str, *, reason: str | None = None) -> Quit:
    return Quit(origin=origin, user_id=user_id, display=display, reason=reason)


@event("config_reload")
def config_reload() -> ConfigReload:
    return ConfigReload()


class Dispatcher:
    """Central event dispatcher; targets filter by type and receive events (AUDIT §1)."""

    def __init__(self) -> None:
        self._targets: list[EventTarget] = []

    def register(self, target: EventTarget) -> None:
        """Register an event target (adapter)."""
        self._targets.append(target)

    def unregister(self, target: EventTarget) -> None:
        """Unregister an event target."""
        if target in self._targets:
            self._targets.remove(target)

    def dispatch(self, source: str, evt: object) -> None:
        """Dispatch event to all targets that accept it."""
        from loguru import logger

        for target in self._targets:
            try:
                if target.accept_event(source, evt):
                    target.push_event(source, evt)
            except Exception as exc:
                logger.exception("Failed to pass event to target {}: {}", target, exc)


dispatcher = Dispatcher()
