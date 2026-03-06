"""Integration tests for echo suppression across all three protocols (CP18).

**Validates: Requirements 17.1, 17.2, 17.3**

These tests verify that messages sent by the bridge are recognized as echoes
and not re-relayed, testing at the adapter-handler flow level rather than
individual utility functions.  Each test wires up realistic adapter state and
feeds a simulated echo through the handler entry-point, asserting that no
event is published to the bus.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Discord echo suppression imports
# ---------------------------------------------------------------------------
from bridge.adapters.discord.handlers import (
    is_bridge_echo,
)

# ---------------------------------------------------------------------------
# IRC echo suppression imports
# ---------------------------------------------------------------------------
from bridge.adapters.irc.handlers import (
    handle_message,
    is_own_echo,
    is_puppet_echo,
    is_relaymsg_echo,
)

# ---------------------------------------------------------------------------
# XMPP echo suppression imports
# ---------------------------------------------------------------------------
from bridge.adapters.xmpp.handlers import (
    is_listener_nick,
    is_recent_echo,
    is_xmpp_echo,
    should_suppress_echo,
)
from bridge.gateway import Bus, ChannelRouter
from cachetools import TTLCache

# ===================================================================
# Shared helpers
# ===================================================================


def _make_bus_and_router() -> tuple[Bus, ChannelRouter]:
    bus = Bus()
    router = ChannelRouter()
    router.load_from_config(
        {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {"server": "irc.example.com", "port": 6667, "tls": False, "channel": "#bridge"},
                    "xmpp": {"muc": "room@muc.example.com"},
                },
            ]
        }
    )
    return bus, router


# ===================================================================
# Discord echo suppression integration tests (Requirement 17.3)
# ===================================================================


class TestDiscordEchoSuppressionIntegration:
    """Verify that webhook-sent and bot-sent messages flow through the
    Discord adapter handler without producing bus events."""

    def _make_discord_adapter(self, bus: Bus, router: ChannelRouter):
        from bridge.adapters.discord import DiscordAdapter

        adapter = DiscordAdapter(bus, router, identity_resolver=None)
        adapter._bot = MagicMock()
        adapter._bot.user.id = 42
        return adapter

    # -- Webhook echo through full handler flow --

    @pytest.mark.asyncio
    async def test_webhook_message_suppressed_in_handler_flow(self) -> None:
        """A webhook-sent message entering on_message must not publish any event."""
        bus, router = _make_bus_and_router()
        adapter = self._make_discord_adapter(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        msg = MagicMock()
        msg.webhook_id = 99999
        msg.author.bot = False
        msg.channel.id = 123
        msg.content = "relayed content"
        msg.attachments = []
        msg.type = MagicMock()
        msg.type.value = 0  # MessageType.default

        await adapter._on_message(msg)
        assert published == [], "Webhook echo should not produce bus events"

    @pytest.mark.asyncio
    async def test_bot_message_suppressed_in_handler_flow(self) -> None:
        """A bot-sent message entering on_message must not publish any event."""
        bus, router = _make_bus_and_router()
        adapter = self._make_discord_adapter(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        msg = MagicMock()
        msg.webhook_id = None
        msg.author.bot = True
        msg.channel.id = 123
        msg.content = "bot echo"
        msg.attachments = []
        msg.type = MagicMock()
        msg.type.value = 0

        await adapter._on_message(msg)
        assert published == [], "Bot echo should not produce bus events"

    # -- Webhook edit echo through handler flow --

    @pytest.mark.asyncio
    async def test_webhook_edit_suppressed_in_handler_flow(self) -> None:
        """A webhook edit event must not publish any event."""
        bus, router = _make_bus_and_router()
        adapter = self._make_discord_adapter(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        payload = MagicMock()
        payload.message = MagicMock()
        payload.message.webhook_id = 99999
        payload.message.author.bot = False
        payload.channel_id = 123

        await adapter._on_raw_message_edit(payload)
        assert published == [], "Webhook edit echo should not produce bus events"

    # -- Reaction echo through handler flow --

    @pytest.mark.asyncio
    async def test_own_reaction_suppressed_in_handler_flow(self) -> None:
        """The bot's own reaction must not publish any event."""
        bus, router = _make_bus_and_router()
        adapter = self._make_discord_adapter(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        payload = MagicMock()
        payload.user_id = 42  # matches bot user id
        payload.emoji.is_unicode_emoji.return_value = True

        await adapter._on_reaction_add(payload)
        assert published == [], "Bot's own reaction should not produce bus events"

    # -- Combined: is_bridge_echo + is_own_reaction work together --

    def test_webhook_and_bot_flags_both_detected(self) -> None:
        """When both webhook_id and author.bot are set, echo is still detected."""
        msg = MagicMock()
        msg.webhook_id = 12345
        msg.author.bot = True
        assert is_bridge_echo(msg) is True

    def test_regular_user_not_suppressed(self) -> None:
        """A regular user message must NOT be detected as echo."""
        msg = MagicMock()
        msg.webhook_id = None
        msg.author.bot = False
        assert is_bridge_echo(msg) is False


# ===================================================================
# IRC echo suppression integration tests (Requirement 17.1)
# ===================================================================


class TestIRCEchoSuppressionIntegration:
    """Verify that echo-message, puppet, and RELAYMSG echoes flow through
    the IRC handler without producing bus events."""

    def _make_irc_client(self, bus: Bus, router: ChannelRouter) -> MagicMock:
        client = MagicMock()
        client.nickname = "bridge"
        client._server = "irc.example.com"
        client._ready = True
        client._router = router
        client._bus = bus
        client._puppet_nick_check = lambda n: n in {"alice_d", "bob_d"}
        client._recent_relaymsg_sends = TTLCache(maxsize=100, ttl=5)
        client._message_tags = {}
        client._msgid_tracker = MagicMock()
        client._pending_sends = asyncio.Queue()
        return client

    # -- Echo-message (own nick) through handle_message --

    @pytest.mark.asyncio
    async def test_own_nick_echo_suppressed_in_handler(self) -> None:
        """A message from the bridge's own nick (echo-message) must not relay."""
        bus, router = _make_bus_and_router()
        client = self._make_irc_client(bus, router)
        client._message_tags = {"msgid": "abc123"}
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        await handle_message(client, "#bridge", "bridge", "hello world")
        assert published == [], "Echo-message from own nick should not relay"

    # -- Puppet echo through handle_message --

    @pytest.mark.asyncio
    async def test_puppet_echo_suppressed_in_handler(self) -> None:
        """A message from a puppet nick must not relay."""
        bus, router = _make_bus_and_router()
        client = self._make_irc_client(bus, router)
        client._message_tags = {}
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        await handle_message(client, "#bridge", "alice_d", "puppet says hi")
        assert published == [], "Puppet echo should not relay"

    # -- RELAYMSG echo via tag through handle_message --

    @pytest.mark.asyncio
    async def test_relaymsg_tag_echo_suppressed_in_handler(self) -> None:
        """A RELAYMSG echo (draft/relaymsg tag matching our nick) must not relay."""
        bus, router = _make_bus_and_router()
        client = self._make_irc_client(bus, router)
        client._message_tags = {"draft/relaymsg": "bridge", "msgid": "relay123"}
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        await handle_message(client, "#bridge", "spoofed_nick/d", "relayed content")
        assert published == [], "RELAYMSG tag echo should not relay"

    # -- RELAYMSG echo via TTLCache fallback --

    @pytest.mark.asyncio
    async def test_relaymsg_cache_echo_suppressed_in_handler(self) -> None:
        """A RELAYMSG echo detected via TTLCache (no tag) must not relay."""
        bus, router = _make_bus_and_router()
        client = self._make_irc_client(bus, router)
        client._message_tags = {}
        # Simulate a recent RELAYMSG send
        client._recent_relaymsg_sends[("irc.example.com", "#bridge", "alice/d")] = None
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        await handle_message(client, "#bridge", "alice/d", "relayed via relaymsg")
        assert published == [], "RELAYMSG TTLCache echo should not relay"

    # -- Combined utility checks at integration level --

    def test_echo_suppression_chain_covers_all_cases(self) -> None:
        """The three echo checks together cover own-nick, puppet, and RELAYMSG."""
        client = MagicMock()
        client.nickname = "bridge"
        client._puppet_nick_check = lambda n: n == "puppet_d"
        client._recent_relaymsg_sends = TTLCache(maxsize=100, ttl=5)
        client._recent_relaymsg_sends[("srv", "#ch", "relay/d")] = None

        # Own nick
        assert is_own_echo(client, "bridge", {}) is True
        # Puppet
        assert is_puppet_echo(client, "puppet_d") is True
        # RELAYMSG cache
        assert is_relaymsg_echo(client, "srv", "#ch", "relay/d", {}) is True
        # External user passes all checks
        assert is_own_echo(client, "alice", {}) is False
        assert is_puppet_echo(client, "alice") is False
        assert is_relaymsg_echo(client, "srv", "#ch", "alice", {}) is False

    def test_relaymsg_tag_detected_as_own_echo(self) -> None:
        """draft/relaymsg tag with our nick is detected by is_own_echo."""
        client = MagicMock()
        client.nickname = "bridge"
        tags = {"draft/relaymsg": "bridge"}
        assert is_own_echo(client, "spoofed_nick", tags) is True

    def test_relaymsg_tag_other_bridge_not_echo(self) -> None:
        """draft/relaymsg tag from a different bridge is not our echo."""
        client = MagicMock()
        client.nickname = "bridge"
        tags = {"draft/relaymsg": "other_bridge"}
        assert is_own_echo(client, "spoofed_nick", tags) is False


# ===================================================================
# XMPP echo suppression integration tests (Requirement 17.2)
# ===================================================================


class TestXMPPEchoSuppressionIntegration:
    """Verify that MUC echoes (puppet JID match, recent-sent-nicks, listener
    nick) are suppressed through the XMPP handler flow."""

    def _make_xmpp_component(self) -> MagicMock:
        comp = MagicMock()
        comp._component_jid = "bridge.example.com"
        comp._recent_sent_nicks = {}
        comp._router = MagicMock()
        comp._msgid_tracker = MagicMock()
        return comp

    def _setup_muc_plugin(self, comp: MagicMock, jid_map: dict[tuple[str, str], str | None]) -> None:
        muc = MagicMock()

        def _get_jid_property(room_jid: str, nick: str, prop: str):
            return jid_map.get((room_jid, nick))

        muc.get_jid_property = _get_jid_property
        comp.plugin = {"xep_0045": muc}

    # -- Puppet JID domain match (primary mechanism) --

    def test_puppet_jid_echo_detected_and_suppressed(self) -> None:
        """A message from a puppet (JID domain matches component) is suppressed."""
        comp = self._make_xmpp_component()
        self._setup_muc_plugin(
            comp,
            {
                ("room@muc.example.com", "alice"): "alice@bridge.example.com/res",
            },
        )
        assert should_suppress_echo(comp, "room@muc.example.com", "alice") is True

    def test_external_user_not_suppressed(self) -> None:
        """A message from an external user (different domain) is NOT suppressed."""
        comp = self._make_xmpp_component()
        self._setup_muc_plugin(
            comp,
            {
                ("room@muc.example.com", "bob"): "bob@users.example.com/client",
            },
        )
        assert should_suppress_echo(comp, "room@muc.example.com", "bob") is False

    # -- Recent-sent-nicks fallback (semi-anonymous MUC) --

    def test_recent_echo_fallback_suppresses(self) -> None:
        """When JID is unavailable, recent-sent-nicks fallback detects the echo."""
        comp = self._make_xmpp_component()
        self._setup_muc_plugin(
            comp,
            {
                ("room@muc.example.com", "puppet"): None,  # JID not exposed
            },
        )
        comp._recent_sent_nicks[("room@muc.example.com", "puppet")] = None
        assert should_suppress_echo(comp, "room@muc.example.com", "puppet") is True

    def test_no_jid_no_recent_not_suppressed(self) -> None:
        """When JID is unavailable and not in recent-sent, message passes through."""
        comp = self._make_xmpp_component()
        self._setup_muc_plugin(
            comp,
            {
                ("room@muc.example.com", "alice"): None,
            },
        )
        assert should_suppress_echo(comp, "room@muc.example.com", "alice") is False

    # -- Listener nick safety net --

    def test_listener_nick_always_suppressed(self) -> None:
        """The bridge listener nick 'bridge' is always suppressed."""
        comp = self._make_xmpp_component()
        self._setup_muc_plugin(comp, {})
        assert should_suppress_echo(comp, "room@muc.example.com", "bridge") is True

    # -- Component JID with @ sign --

    def test_component_jid_with_at_sign_echo_detected(self) -> None:
        """Component JID like 'bridge@component.example.com' uses domain part."""
        comp = self._make_xmpp_component()
        comp._component_jid = "bridge@component.example.com"
        self._setup_muc_plugin(
            comp,
            {
                ("room@muc.example.com", "puppet"): "puppet@component.example.com/res",
            },
        )
        assert is_xmpp_echo(comp, "room@muc.example.com", "puppet") is True

    # -- Priority order: JID check > recent-sent > listener --

    def test_suppression_priority_jid_first(self) -> None:
        """JID-based detection takes priority over recent-sent-nicks."""
        comp = self._make_xmpp_component()
        self._setup_muc_plugin(
            comp,
            {
                ("room@muc.example.com", "puppet"): "puppet@bridge.example.com/res",
            },
        )
        # Also in recent-sent (both should detect, but JID is primary)
        comp._recent_sent_nicks[("room@muc.example.com", "puppet")] = None
        assert is_xmpp_echo(comp, "room@muc.example.com", "puppet") is True
        assert should_suppress_echo(comp, "room@muc.example.com", "puppet") is True

    def test_suppression_all_three_checks_combined(self) -> None:
        """Verify all three echo detection mechanisms work in combination."""
        comp = self._make_xmpp_component()
        self._setup_muc_plugin(
            comp,
            {
                ("room@muc.example.com", "puppet"): "puppet@bridge.example.com/res",
                ("room@muc.example.com", "external"): "ext@users.example.com/client",
            },
        )
        comp._recent_sent_nicks[("room@muc.example.com", "recent_puppet")] = None

        # JID match → suppressed
        assert should_suppress_echo(comp, "room@muc.example.com", "puppet") is True
        # Recent-sent → suppressed (JID returns None for this nick)
        assert should_suppress_echo(comp, "room@muc.example.com", "recent_puppet") is True
        # Listener nick → suppressed
        assert should_suppress_echo(comp, "room@muc.example.com", "bridge") is True
        # External user → NOT suppressed
        assert should_suppress_echo(comp, "room@muc.example.com", "external") is False


# ===================================================================
# Cross-protocol integration: all three protocols suppress echoes
# ===================================================================


class TestCrossProtocolEchoSuppression:
    """Verify that echo suppression works consistently across all protocols —
    the bridge never re-relays its own messages regardless of protocol."""

    def test_discord_echo_detected(self) -> None:
        """Discord: webhook and bot messages are both detected as echoes."""
        webhook_msg = MagicMock(webhook_id=99999)
        webhook_msg.author.bot = False
        assert is_bridge_echo(webhook_msg) is True

        bot_msg = MagicMock(webhook_id=None)
        bot_msg.author.bot = True
        assert is_bridge_echo(bot_msg) is True

    def test_irc_echo_detected(self) -> None:
        """IRC: own-nick, puppet, and RELAYMSG echoes are all detected."""
        client = MagicMock()
        client.nickname = "bridge"
        client._puppet_nick_check = lambda n: n == "puppet_d"
        client._recent_relaymsg_sends = TTLCache(maxsize=100, ttl=5)
        client._recent_relaymsg_sends[("srv", "#ch", "relay/d")] = None

        assert is_own_echo(client, "bridge", {}) is True
        assert is_puppet_echo(client, "puppet_d") is True
        assert is_relaymsg_echo(client, "srv", "#ch", "relay/d", {}) is True

    def test_xmpp_echo_detected(self) -> None:
        """XMPP: puppet JID, recent-sent, and listener nick are all detected."""
        comp = MagicMock()
        comp._component_jid = "bridge.example.com"
        comp._recent_sent_nicks = {("room@muc.example.com", "puppet"): None}

        muc = MagicMock()
        muc.get_jid_property = lambda r, n, p: "puppet@bridge.example.com/res" if n == "jid_puppet" else None
        comp.plugin = {"xep_0045": muc}

        assert is_xmpp_echo(comp, "room@muc.example.com", "jid_puppet") is True
        assert is_recent_echo(comp, "room@muc.example.com", "puppet") is True
        assert is_listener_nick("bridge") is True

    def test_non_echo_messages_pass_through_all_protocols(self) -> None:
        """Regular user messages are NOT detected as echoes on any protocol."""
        # Discord
        user_msg = MagicMock(webhook_id=None)
        user_msg.author.bot = False
        assert is_bridge_echo(user_msg) is False

        # IRC
        client = MagicMock()
        client.nickname = "bridge"
        client._puppet_nick_check = lambda n: False
        client._recent_relaymsg_sends = TTLCache(maxsize=100, ttl=5)
        assert is_own_echo(client, "alice", {}) is False
        assert is_puppet_echo(client, "alice") is False
        assert is_relaymsg_echo(client, "srv", "#ch", "alice", {}) is False

        # XMPP
        comp = MagicMock()
        comp._component_jid = "bridge.example.com"
        comp._recent_sent_nicks = {}
        muc = MagicMock()
        muc.get_jid_property = lambda r, n, p: "alice@users.example.com/client"
        comp.plugin = {"xep_0045": muc}
        assert should_suppress_echo(comp, "room@muc.example.com", "alice") is False
