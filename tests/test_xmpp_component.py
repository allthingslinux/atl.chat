"""Tests for XMPPComponent event handlers (_on_groupchat_message, _on_reactions, _on_retraction)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")

from bridge.adapters.xmpp_component import XMPPComponent
from bridge.adapters.xmpp_msgid import XMPPMessageIDTracker
from bridge.events import MessageDelete, MessageIn, ReactionIn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_component(router=None, bus=None):
    """Instantiate XMPPComponent bypassing slixmpp's __init__."""
    comp = object.__new__(XMPPComponent)
    comp._bus = bus or MagicMock()
    comp._router = router or MagicMock()
    comp._identity = MagicMock()
    comp._component_jid = "bridge.example.com"
    comp._avatar_cache = {}
    comp._ibb_streams = {}
    comp._msgid_tracker = XMPPMessageIDTracker()
    return comp


class MockPlugin:
    """Minimal plugin stub with get() support."""
    def __init__(self, data=None):
        self._data = data or {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def get_values(self):
        return self._data.get("values", [])


class MockMsg:
    """Minimal slixmpp message stanza stub."""

    def __init__(self, from_jid, body="hello", mucnick="nick", msg_id="msg-1", plugins=None):
        self._from = from_jid
        self._body = body
        self._mucnick = mucnick
        self._id = msg_id
        self._plugins: dict[str, object] = plugins or {}

    def __getitem__(self, key):
        if key == "from":
            return self._from
        if key == "body":
            return self._body
        if key == "mucnick":
            return self._mucnick
        # For nested access like msg["replace"]["id"] return a dict-like mock
        return MagicMock()

    def get_plugin(self, name, check=False):
        return self._plugins.get(name)

    def get(self, key, default=None):
        if key == "id":
            return self._id
        return default


# ---------------------------------------------------------------------------
# _on_groupchat_message
# ---------------------------------------------------------------------------

class TestOnGroupchatMessage:
    def _make_router(self, discord_channel_id="123"):
        router = MagicMock()
        mapping = MagicMock()
        mapping.discord_channel_id = discord_channel_id
        router.get_mapping_for_xmpp.return_value = mapping
        return router

    def test_normal_message_publishes_message_in(self):
        router = self._make_router()
        bus = MagicMock()
        comp = make_component(router=router, bus=bus)

        msg = MockMsg(from_jid="room@conf.example.com/nick", body="hello", mucnick="nick", msg_id="xmpp-1")
        comp._on_groupchat_message(msg)

        bus.publish.assert_called_once()
        source, evt = bus.publish.call_args[0]
        assert source == "xmpp"
        assert isinstance(evt, MessageIn)
        assert evt.content == "hello"
        assert evt.author_display == "nick"
        assert evt.channel_id == "123"
        assert evt.message_id == "xmpp-1"
        assert evt.is_edit is False

    def test_delayed_message_is_skipped(self):
        router = self._make_router()
        bus = MagicMock()
        comp = make_component(router=router, bus=bus)

        msg = MockMsg("room@conf.example.com/nick", plugins={"delay": MockPlugin()})
        comp._on_groupchat_message(msg)

        bus.publish.assert_not_called()

    def test_no_mapping_is_skipped(self):
        router = MagicMock()
        router.get_mapping_for_xmpp.return_value = None
        bus = MagicMock()
        comp = make_component(router=router, bus=bus)

        msg = MockMsg("room@conf.example.com/nick")
        comp._on_groupchat_message(msg)

        bus.publish.assert_not_called()

    def test_spoiler_body_wrapped(self):
        router = self._make_router()
        bus = MagicMock()
        comp = make_component(router=router, bus=bus)

        msg = MockMsg("room@conf.example.com/nick", body="secret", plugins={"spoiler": MockPlugin()})
        comp._on_groupchat_message(msg)

        _, evt = bus.publish.call_args[0]
        assert evt.content == "||secret||"

    def test_edit_message_sets_is_edit_and_raw(self):
        router = self._make_router()
        bus = MagicMock()
        comp = make_component(router=router, bus=bus)

        replace_plugin = MockPlugin({"id": "orig-id"})
        msg = MockMsg("room@conf.example.com/nick", plugins={"replace": replace_plugin})
        # Patch __getitem__ for msg["replace"]["id"]
        msg._replace_id = "orig-id"

        # We need msg["replace"]["id"] to work — override __getitem__
        class MsgWithReplace(MockMsg):
            def __getitem__(self, key):
                if key == "replace":
                    return {"id": "orig-id"}
                return super().__getitem__(key)

        msg2 = MsgWithReplace("room@conf.example.com/nick", plugins={"replace": replace_plugin})
        comp._on_groupchat_message(msg2)

        _, evt = bus.publish.call_args[0]
        assert evt.is_edit is True
        assert evt.raw.get("replace_id") == "orig-id"

    def test_reply_xep_0461_sets_reply_to_id(self):
        router = self._make_router()
        bus = MagicMock()
        comp = make_component(router=router, bus=bus)

        reply_plugin = MockPlugin({"id": "reply-target"})

        class MsgWithReply(MockMsg):
            def __getitem__(self, key):
                if key == "reply":
                    return {"id": "reply-target"}
                return super().__getitem__(key)

        msg = MsgWithReply("room@conf.example.com/nick", plugins={"reply": reply_plugin})
        comp._on_groupchat_message(msg)

        _, evt = bus.publish.call_args[0]
        assert evt.raw.get("reply_to_id") == "reply-target"

    def test_reply_xep_0372_fallback(self):
        router = self._make_router()
        bus = MagicMock()
        comp = make_component(router=router, bus=bus)

        ref_plugin = MockPlugin({"type": "reply", "uri": "xmpp:room@conf.example.com?id=ref-target"})

        class MsgWithRef(MockMsg):
            def __getitem__(self, key):
                if key == "reference":
                    return {"type": "reply", "uri": "xmpp:room@conf.example.com?id=ref-target"}
                return super().__getitem__(key)

        msg = MsgWithRef("room@conf.example.com/nick", plugins={"reference": ref_plugin})
        comp._on_groupchat_message(msg)

        _, evt = bus.publish.call_args[0]
        assert evt.raw.get("reply_to_id") == "ref-target"

    def test_from_jid_without_slash_uses_full_jid_as_room(self):
        router = MagicMock()
        router.get_mapping_for_xmpp.return_value = None
        comp = make_component(router=router)

        msg = MockMsg("room@conf.example.com")  # no slash
        comp._on_groupchat_message(msg)

        router.get_mapping_for_xmpp.assert_called_once_with("room@conf.example.com")


# ---------------------------------------------------------------------------
# _on_reactions
# ---------------------------------------------------------------------------

class TestOnReactions:
    def _make_router(self, discord_channel_id="123"):
        router = MagicMock()
        mapping = MagicMock()
        mapping.discord_channel_id = discord_channel_id
        router.get_mapping_for_xmpp.return_value = mapping
        return router

    def test_reaction_publishes_reaction_in(self):
        router = self._make_router()
        bus = MagicMock()
        comp = make_component(router=router, bus=bus)
        comp._msgid_tracker.store("xmpp-1", "discord-1", "room@conf.example.com")

        reactions_plugin = MockPlugin({"id": "xmpp-1", "values": ["👍"]})

        class ReactionMsg(MockMsg):
            def __getitem__(self, key):
                if key == "from":
                    return self._from
                return super().__getitem__(key)

        msg = MockMsg("room@conf.example.com/nick", plugins={"reactions": reactions_plugin})
        comp._on_reactions(msg)

        bus.publish.assert_called_once()
        source, evt = bus.publish.call_args[0]
        assert source == "xmpp"
        assert isinstance(evt, ReactionIn)
        assert evt.emoji == "👍"
        assert evt.message_id == "discord-1"
        assert evt.author_display == "nick"

    def test_no_mapping_skips(self):
        router = MagicMock()
        router.get_mapping_for_xmpp.return_value = None
        bus = MagicMock()
        comp = make_component(router=router, bus=bus)

        msg = MockMsg("room@conf.example.com/nick")
        comp._on_reactions(msg)
        bus.publish.assert_not_called()

    def test_from_jid_without_slash_returns_early(self):
        bus = MagicMock()
        comp = make_component(bus=bus)

        msg = MockMsg("room@conf.example.com")  # no slash
        comp._on_reactions(msg)
        bus.publish.assert_not_called()

    def test_no_reactions_plugin_skips(self):
        router = self._make_router()
        bus = MagicMock()
        comp = make_component(router=router, bus=bus)

        msg = MockMsg("room@conf.example.com/nick")  # no reactions plugin
        comp._on_reactions(msg)
        bus.publish.assert_not_called()

    def test_no_discord_id_in_tracker_skips(self):
        router = self._make_router()
        bus = MagicMock()
        comp = make_component(router=router, bus=bus)
        # tracker has no entry for "xmpp-unknown"
        reactions_plugin = MockPlugin({"id": "xmpp-unknown", "values": ["👍"]})
        msg = MockMsg("room@conf.example.com/nick", plugins={"reactions": reactions_plugin})
        comp._on_reactions(msg)
        bus.publish.assert_not_called()

    def test_multiple_emojis_publishes_multiple_events(self):
        router = self._make_router()
        bus = MagicMock()
        comp = make_component(router=router, bus=bus)
        comp._msgid_tracker.store("xmpp-1", "discord-1", "room@conf.example.com")

        reactions_plugin = MockPlugin({"id": "xmpp-1", "values": ["👍", "❤️"]})
        msg = MockMsg("room@conf.example.com/nick", plugins={"reactions": reactions_plugin})
        comp._on_reactions(msg)

        assert bus.publish.call_count == 2


# ---------------------------------------------------------------------------
# _on_retraction
# ---------------------------------------------------------------------------

class TestOnRetraction:
    def _make_router(self, discord_channel_id="123"):
        router = MagicMock()
        mapping = MagicMock()
        mapping.discord_channel_id = discord_channel_id
        router.get_mapping_for_xmpp.return_value = mapping
        return router

    def test_retraction_publishes_message_delete(self):
        router = self._make_router()
        bus = MagicMock()
        comp = make_component(router=router, bus=bus)
        comp._msgid_tracker.store("xmpp-1", "discord-1", "room@conf.example.com")

        retract_plugin = MockPlugin({"id": "xmpp-1"})
        msg = MockMsg("room@conf.example.com/nick", plugins={"retract": retract_plugin})
        comp._on_retraction(msg)

        bus.publish.assert_called_once()
        source, evt = bus.publish.call_args[0]
        assert source == "xmpp"
        assert isinstance(evt, MessageDelete)
        assert evt.message_id == "discord-1"
        assert evt.channel_id == "room@conf.example.com"

    def test_no_mapping_skips(self):
        router = MagicMock()
        router.get_mapping_for_xmpp.return_value = None
        bus = MagicMock()
        comp = make_component(router=router, bus=bus)

        retract_plugin = MockPlugin({"id": "xmpp-1"})
        msg = MockMsg("room@conf.example.com/nick", plugins={"retract": retract_plugin})
        comp._on_retraction(msg)
        bus.publish.assert_not_called()

    def test_from_jid_without_slash_returns_early(self):
        bus = MagicMock()
        comp = make_component(bus=bus)

        msg = MockMsg("room@conf.example.com")
        comp._on_retraction(msg)
        bus.publish.assert_not_called()

    def test_no_retract_plugin_skips(self):
        router = self._make_router()
        bus = MagicMock()
        comp = make_component(router=router, bus=bus)

        msg = MockMsg("room@conf.example.com/nick")  # no retract plugin
        comp._on_retraction(msg)
        bus.publish.assert_not_called()

    def test_no_discord_id_in_tracker_skips(self):
        router = self._make_router()
        bus = MagicMock()
        comp = make_component(router=router, bus=bus)

        retract_plugin = MockPlugin({"id": "xmpp-unknown"})
        msg = MockMsg("room@conf.example.com/nick", plugins={"retract": retract_plugin})
        comp._on_retraction(msg)
        bus.publish.assert_not_called()
