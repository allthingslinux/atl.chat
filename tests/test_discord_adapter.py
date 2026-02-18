"""Tests for Discord adapter."""

from __future__ import annotations

import pytest

from bridge.events import MessageIn, MessageOut
from bridge.gateway import Bus, ChannelRouter


@pytest.fixture
def bus() -> Bus:
    return Bus()


@pytest.fixture
def router() -> ChannelRouter:
    r = ChannelRouter()
    r.load_from_config(
        {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {"server": "s", "port": 6667, "tls": False, "channel": "#c"},
                },
            ]
        }
    )
    return r


def test_discord_adapter_accepts_message_out_for_discord(bus: Bus, router: ChannelRouter) -> None:
    """Discord adapter accepts MessageOut with target_origin=discord."""
    from bridge.adapters.disc import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    assert adapter.accept_event("irc", MessageOut("discord", "123", "u1", "Alice", "hi", "m1"))
    assert not adapter.accept_event("irc", MessageOut("irc", "123", "u1", "Alice", "hi", "m1"))
    assert not adapter.accept_event("irc", MessageIn("irc", "123", "u1", "Alice", "hi", "m1"))


def test_ensure_valid_username() -> None:
    """Webhook usernames are 2-32 chars (AUDIT §3)."""
    from bridge.adapters.disc import _ensure_valid_username

    assert len(_ensure_valid_username("A")) >= 2
    assert len(_ensure_valid_username("x" * 50)) == 32
    assert _ensure_valid_username("Alice") == "Alice"
