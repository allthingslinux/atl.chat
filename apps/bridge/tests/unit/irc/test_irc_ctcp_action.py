"""Tests for IRC CTCP ACTION handling (Requirements 19.1, 19.2, 19.3).

Verifies that the handler emits the correct MessageIn event with
is_action=True and the expected content format.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from bridge.adapters.irc.handlers import handle_ctcp_action
from bridge.gateway import Bus, ChannelRouter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
                    "irc": {"server": "irc.example.com", "port": 6667, "tls": False, "channel": "#test"},
                },
            ]
        }
    )
    return r


def _make_client(bus: Bus, router: ChannelRouter, nickname: str = "bridge") -> MagicMock:
    """Create a minimal mock IRCClient for handler testing."""
    client = MagicMock()
    client.nickname = nickname
    client._bus = bus
    client._router = router
    client._server = "irc.example.com"
    client._ready = True
    client._puppet_nick_check = None
    client._message_tags = {}
    client._recent_relaymsg_sends = {}
    return client


# ---------------------------------------------------------------------------
# handle_ctcp_action — unit tests
# ---------------------------------------------------------------------------


class TestHandleCtcpAction:
    """Verify handle_ctcp_action emits MessageIn with action flag."""

    @pytest.mark.asyncio
    async def test_action_emits_message_in_with_action_flag(self, bus: Bus, router: ChannelRouter) -> None:
        client = _make_client(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        await handle_ctcp_action(client, "alice", "#test", "waves hello")

        assert len(published) == 1
        source, evt = published[0]
        assert source == "irc"
        assert evt.is_action is True

    @pytest.mark.asyncio
    async def test_action_content_format(self, bus: Bus, router: ChannelRouter) -> None:
        client = _make_client(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        await handle_ctcp_action(client, "bob", "#test", "dances")

        assert len(published) == 1
        _, evt = published[0]
        assert evt.content == "* bob dances"

    @pytest.mark.asyncio
    async def test_action_author_is_set(self, bus: Bus, router: ChannelRouter) -> None:
        client = _make_client(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        await handle_ctcp_action(client, "charlie", "#test", "shrugs")

        _, evt = published[0]
        assert evt.author_id == "charlie"
        assert evt.author_display == "charlie"

    @pytest.mark.asyncio
    async def test_own_action_suppressed(self, bus: Bus, router: ChannelRouter) -> None:
        """Bridge's own /me actions should not be relayed."""
        client = _make_client(bus, router, nickname="bridge")
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        await handle_ctcp_action(client, "bridge", "#test", "does something")

        assert len(published) == 0

    @pytest.mark.asyncio
    async def test_private_action_ignored(self, bus: Bus, router: ChannelRouter) -> None:
        """Actions to non-channel targets should be ignored."""
        client = _make_client(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        await handle_ctcp_action(client, "alice", "bridge", "waves")

        assert len(published) == 0

    @pytest.mark.asyncio
    async def test_unmapped_channel_ignored(self, bus: Bus, router: ChannelRouter) -> None:
        """Actions in unmapped channels should be ignored."""
        client = _make_client(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        await handle_ctcp_action(client, "alice", "#unmapped", "waves")

        assert len(published) == 0
