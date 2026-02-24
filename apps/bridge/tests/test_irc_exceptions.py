"""Test IRC adapter with pydle."""

from unittest.mock import AsyncMock, Mock

import pytest

from bridge.adapters.irc import IRCAdapter, IRCClient
from bridge.adapters.irc_msgid import MessageIDTracker
from bridge.adapters.irc_puppet import IRCPuppet, IRCPuppetManager


class TestIRCClient:
    """Test pydle-based IRC client."""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        bus = Mock()
        router = Mock()
        tracker = MessageIDTracker()

        client = IRCClient(
            bus=bus,
            router=router,
            server="irc.libera.chat",
            nick="test-bot",
            channels=["#test"],
            msgid_tracker=tracker,
        )

        # Nickname is set during connection, not init
        assert client._server == "irc.libera.chat"
        assert client._channels == ["#test"]

    @pytest.mark.asyncio
    async def test_message_id_extraction(self):
        bus = Mock()
        router = Mock()
        router.get_mapping_for_irc = Mock(return_value=Mock(discord_channel_id="123"))
        tracker = MessageIDTracker()

        client = IRCClient(
            bus=bus,
            router=router,
            server="irc.libera.chat",
            nick="test-bot",
            channels=["#test"],
            msgid_tracker=tracker,
        )

        client._message_tags = {"msgid": "abc123", "+draft/reply": "xyz789"}
        client._ready = True

        await client.on_message("#test", "user", "Hello")

        assert bus.publish.called
        _, evt = bus.publish.call_args[0]
        assert evt.message_id == "abc123"
        assert evt.content == "Hello"
        assert evt.author_id == "user"


class TestMessageIDTracker:
    """Test message ID tracking."""

    def test_store_and_retrieve(self):
        tracker = MessageIDTracker()

        tracker.store("irc-msgid-123", "discord-456")

        assert tracker.get_discord_id("irc-msgid-123") == "discord-456"
        assert tracker.get_irc_msgid("discord-456") == "irc-msgid-123"

    def test_missing_mapping(self):
        tracker = MessageIDTracker()

        assert tracker.get_discord_id("nonexistent") is None
        assert tracker.get_irc_msgid("nonexistent") is None


class TestIRCPuppet:
    """Test IRC puppet connections."""

    def test_puppet_initialization(self):
        puppet = IRCPuppet("user-nick", "discord-123")

        # Nickname is set during connection, not init
        assert puppet.discord_id == "discord-123"

    def test_puppet_touch_updates_activity(self):
        import time

        puppet = IRCPuppet("user-nick", "discord-123")
        initial = puppet.last_activity

        time.sleep(0.01)
        puppet.touch()

        assert puppet.last_activity > initial


class TestIRCPuppetManager:
    """Test puppet manager."""

    @pytest.mark.asyncio
    async def test_manager_initialization(self):
        bus = Mock()
        router = Mock()
        identity = Mock()

        manager = IRCPuppetManager(
            bus=bus,
            router=router,
            identity=identity,
            server="irc.libera.chat",
            port=6697,
            tls=True,
        )

        assert manager._server == "irc.libera.chat"
        assert manager._port == 6697
        assert manager._tls is True

    @pytest.mark.asyncio
    async def test_get_puppet_without_identity(self):
        bus = Mock()
        router = Mock()
        identity = AsyncMock()
        identity.discord_to_irc = AsyncMock(return_value=None)

        manager = IRCPuppetManager(
            bus=bus,
            router=router,
            identity=identity,
            server="irc.libera.chat",
            port=6697,
            tls=True,
        )

        puppet = await manager.get_or_create_puppet("discord-123")

        assert puppet is None


class TestIRCAdapter:
    """Test IRC adapter."""

    @pytest.mark.asyncio
    async def test_adapter_initialization(self):
        from bridge.gateway.bus import Bus
        from bridge.gateway.router import ChannelRouter

        bus = Bus()
        router = ChannelRouter()
        adapter = IRCAdapter(bus, router, identity_resolver=None)

        assert adapter.name == "irc"
        assert adapter._msgid_tracker is not None

    def test_adapter_accepts_irc_messages(self):
        from bridge.events import MessageOut
        from bridge.gateway.bus import Bus
        from bridge.gateway.router import ChannelRouter

        bus = Bus()
        router = ChannelRouter()
        adapter = IRCAdapter(bus, router, identity_resolver=None)

        msg = MessageOut(
            target_origin="irc",
            channel_id="123",
            author_id="user1",
            author_display="User",
            content="Test",
            message_id="msg1",
        )

        assert adapter.accept_event("discord", msg) is True

    def test_adapter_rejects_non_irc_messages(self):
        from bridge.events import MessageOut
        from bridge.gateway.bus import Bus
        from bridge.gateway.router import ChannelRouter

        bus = Bus()
        router = ChannelRouter()
        adapter = IRCAdapter(bus, router, identity_resolver=None)

        msg = MessageOut(
            target_origin="xmpp",
            channel_id="123",
            author_id="user1",
            author_display="User",
            content="Test",
            message_id="msg1",
        )

        assert adapter.accept_event("discord", msg) is False
