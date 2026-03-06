"""Tests for Discord echo suppression (Requirement 17.3).

Verifies that the bridge recognises its own messages (webhook-sent and bot-sent)
and its own reactions, preventing infinite relay loops.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from bridge.adapters.discord.handlers import is_bridge_echo, is_own_reaction
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
                    "irc": {"server": "s", "port": 6667, "tls": False, "channel": "#c"},
                },
            ]
        }
    )
    return r


def _make_adapter(bus: Bus, router: ChannelRouter):
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    adapter._bot = MagicMock()
    adapter._bot.user.id = 42
    return adapter


# ---------------------------------------------------------------------------
# is_bridge_echo — unit tests
# ---------------------------------------------------------------------------


class TestIsBridgeEcho:
    """Unit tests for the centralised is_bridge_echo() utility."""

    def test_webhook_message_is_echo(self) -> None:
        msg = MagicMock()
        msg.webhook_id = 99999
        msg.author.bot = False
        assert is_bridge_echo(msg) is True

    def test_bot_message_is_echo(self) -> None:
        msg = MagicMock()
        msg.webhook_id = None
        msg.author.bot = True
        assert is_bridge_echo(msg) is True

    def test_regular_user_message_is_not_echo(self) -> None:
        msg = MagicMock()
        msg.webhook_id = None
        msg.author.bot = False
        assert is_bridge_echo(msg) is False

    def test_webhook_and_bot_both_set_is_echo(self) -> None:
        msg = MagicMock()
        msg.webhook_id = 12345
        msg.author.bot = True
        assert is_bridge_echo(msg) is True

    def test_missing_webhook_id_attr_is_not_echo(self) -> None:
        """Messages without a webhook_id attribute at all should not crash."""
        msg = MagicMock(spec=[])  # no attributes
        msg.author = MagicMock()
        msg.author.bot = False
        # getattr(msg, "webhook_id", None) returns None for missing attr
        assert is_bridge_echo(msg) is False


# ---------------------------------------------------------------------------
# is_own_reaction — unit tests
# ---------------------------------------------------------------------------


class TestIsOwnReaction:
    """Unit tests for the centralised is_own_reaction() utility."""

    def test_own_reaction_detected(self, bus: Bus, router: ChannelRouter) -> None:
        adapter = _make_adapter(bus, router)
        payload = MagicMock()
        payload.user_id = 42  # matches bot user id
        assert is_own_reaction(adapter, payload) is True

    def test_other_user_reaction_not_detected(self, bus: Bus, router: ChannelRouter) -> None:
        adapter = _make_adapter(bus, router)
        payload = MagicMock()
        payload.user_id = 999
        assert is_own_reaction(adapter, payload) is False

    def test_no_bot_returns_false(self, bus: Bus, router: ChannelRouter) -> None:
        adapter = _make_adapter(bus, router)
        adapter._bot = None
        payload = MagicMock()
        payload.user_id = 42
        assert is_own_reaction(adapter, payload) is False

    def test_no_user_id_returns_false(self, bus: Bus, router: ChannelRouter) -> None:
        adapter = _make_adapter(bus, router)
        payload = MagicMock(spec=[])  # no user_id attribute
        assert is_own_reaction(adapter, payload) is False


# ---------------------------------------------------------------------------
# Handler-level integration: on_message echo suppression
# ---------------------------------------------------------------------------


class TestOnMessageEchoSuppression:
    """Verify on_message drops webhook and bot messages."""

    @pytest.mark.asyncio
    async def test_webhook_message_not_relayed(self, bus: Bus, router: ChannelRouter) -> None:
        adapter = _make_adapter(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        msg = MagicMock()
        msg.webhook_id = 99999
        msg.author.bot = False
        msg.channel.id = 123
        msg.content = "bridge relayed this"
        msg.attachments = []

        await adapter._on_message(msg)
        assert len(published) == 0

    @pytest.mark.asyncio
    async def test_bot_message_not_relayed(self, bus: Bus, router: ChannelRouter) -> None:
        adapter = _make_adapter(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        msg = MagicMock()
        msg.webhook_id = None
        msg.author.bot = True
        msg.channel.id = 123
        msg.content = "bot says hi"
        msg.attachments = []

        await adapter._on_message(msg)
        assert len(published) == 0


# ---------------------------------------------------------------------------
# Handler-level integration: on_raw_message_edit echo suppression
# ---------------------------------------------------------------------------


class TestOnRawMessageEditEchoSuppression:
    """Verify on_raw_message_edit drops webhook and bot edits."""

    @pytest.mark.asyncio
    async def test_webhook_edit_not_relayed(self, bus: Bus, router: ChannelRouter) -> None:
        adapter = _make_adapter(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        payload = MagicMock()
        payload.message.webhook_id = 99999
        payload.message.author.bot = False
        payload.channel_id = 123

        await adapter._on_raw_message_edit(payload)
        assert len(published) == 0

    @pytest.mark.asyncio
    async def test_bot_edit_not_relayed(self, bus: Bus, router: ChannelRouter) -> None:
        adapter = _make_adapter(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        payload = MagicMock()
        payload.message.webhook_id = None
        payload.message.author.bot = True
        payload.channel_id = 123

        await adapter._on_raw_message_edit(payload)
        assert len(published) == 0


# ---------------------------------------------------------------------------
# Handler-level integration: reaction echo suppression
# ---------------------------------------------------------------------------


class TestReactionEchoSuppression:
    """Verify on_reaction_add/remove drops the bot's own reactions."""

    @pytest.mark.asyncio
    async def test_own_reaction_add_not_relayed(self, bus: Bus, router: ChannelRouter) -> None:
        adapter = _make_adapter(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        payload = MagicMock()
        payload.user_id = 42  # bot's own user id
        payload.emoji.is_unicode_emoji.return_value = True

        await adapter._on_reaction_add(payload)
        assert len(published) == 0

    @pytest.mark.asyncio
    async def test_own_reaction_remove_not_relayed(self, bus: Bus, router: ChannelRouter) -> None:
        adapter = _make_adapter(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        payload = MagicMock()
        payload.user_id = 42  # bot's own user id
        payload.emoji.is_unicode_emoji.return_value = True

        await adapter._on_reaction_remove(payload)
        assert len(published) == 0
