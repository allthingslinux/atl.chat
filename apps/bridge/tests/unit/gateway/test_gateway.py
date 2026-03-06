"""Tests for gateway bus and router."""

from __future__ import annotations

from bridge.events import MessageIn
from bridge.gateway import Bus, ChannelRouter


class SimpleTarget:
    """Simple target that collects MessageIn."""

    def __init__(self) -> None:
        self.events: list[tuple[str, object]] = []

    def accept_event(self, source: str, evt: object) -> bool:
        return isinstance(evt, MessageIn)

    def push_event(self, source: str, evt: object) -> None:
        self.events.append((source, evt))


def test_bus_publish_reaches_targets() -> None:
    """Bus publish dispatches to registered targets."""
    bus = Bus()
    target = SimpleTarget()
    bus.register(target)

    bus.publish(
        "discord",
        MessageIn("discord", "c1", "u1", "Alice", "hi", "m1"),
    )
    assert len(target.events) == 1
    evt = target.events[0][1]
    assert isinstance(evt, MessageIn)
    assert evt.content == "hi"


def test_router_load_from_config() -> None:
    """Router loads mappings from config."""
    router = ChannelRouter()
    config = {
        "mappings": [
            {
                "discord_channel_id": "123",
                "irc": {"server": "irc.test", "port": 6667, "tls": False, "channel": "#test"},
                "xmpp": {"muc_jid": "test@muc.test"},
            },
        ]
    }
    router.load_from_config(config)

    mappings = router.all_mappings()
    assert len(mappings) == 1
    m = mappings[0]
    assert m.discord_channel_id == "123"
    assert m.irc is not None
    assert m.irc.server == "irc.test"
    assert m.irc.channel == "#test"
    assert m.xmpp is not None
    assert m.xmpp.muc_jid == "test@muc.test"


def test_router_get_mapping_for_discord() -> None:
    """Router finds mapping by Discord channel ID."""
    router = ChannelRouter()
    router.load_from_config(
        {
            "mappings": [
                {
                    "discord_channel_id": "456",
                    "irc": {"server": "s", "port": 6667, "tls": False, "channel": "#c"},
                }
            ]
        }
    )
    m = router.get_mapping_for_discord("456")
    assert m is not None
    assert m.discord_channel_id == "456"

    assert router.get_mapping_for_discord("999") is None


def test_router_get_mapping_for_irc() -> None:
    """Router finds mapping by IRC server/channel."""
    router = ChannelRouter()
    router.load_from_config(
        {
            "mappings": [
                {
                    "discord_channel_id": "1",
                    "irc": {"server": "irc.atl", "port": 6697, "tls": True, "channel": "#bridge"},
                },
            ]
        }
    )
    m = router.get_mapping_for_irc("irc.atl", "#bridge")
    assert m is not None
    assert m.discord_channel_id == "1"

    assert router.get_mapping_for_irc("other", "#other") is None
