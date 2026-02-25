"""Tests for XMPPAdapter (bridge/adapters/xmpp.py)."""

from __future__ import annotations

import asyncio
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bridge.adapters.xmpp import XMPPAdapter
from bridge.events import MessageDeleteOut, MessageOut, ReactionOut
from bridge.gateway import Bus, ChannelRouter
from bridge.gateway.router import ChannelMapping, XmppTarget

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_adapter(
    mappings: list[ChannelMapping] | None = None,
    identity_nick: str | None = "xmpp_user",
) -> tuple[XMPPAdapter, MagicMock, MagicMock]:
    """Return (adapter, mock_bus, mock_router)."""
    bus = MagicMock(spec=Bus)
    router = MagicMock(spec=ChannelRouter)

    if mappings is not None:
        router.all_mappings.return_value = mappings
    else:
        router.all_mappings.return_value = []

    identity = AsyncMock()
    identity.discord_to_xmpp = AsyncMock(return_value=identity_nick)

    adapter = XMPPAdapter(bus, router, identity)
    return adapter, bus, router


def _xmpp_mapping(discord_id: str = "111", muc: str = "room@conf.example.com") -> ChannelMapping:
    return ChannelMapping(discord_channel_id=discord_id, irc=None, xmpp=XmppTarget(muc_jid=muc))


def _mock_component(xmpp_id_for: str | None = "xmpp-msg-1") -> MagicMock:
    """Return a mock XMPPComponent."""
    comp = MagicMock()
    comp._msgid_tracker = MagicMock()
    comp._msgid_tracker.get_xmpp_id.return_value = xmpp_id_for
    comp._msgid_tracker.get_xmpp_id_for_reaction.return_value = xmpp_id_for
    comp.send_message_as_user = AsyncMock(return_value="xmpp-new-id")
    comp.send_correction_as_user = AsyncMock()
    comp.send_retraction_as_user = AsyncMock()
    comp.send_reaction_as_user = AsyncMock()
    comp.set_avatar_for_user = AsyncMock()
    comp.disconnect = MagicMock()
    return comp


# ---------------------------------------------------------------------------
# name
# ---------------------------------------------------------------------------


def test_name():
    adapter, _, _ = _make_adapter()
    assert adapter.name == "xmpp"


# ---------------------------------------------------------------------------
# accept_event
# ---------------------------------------------------------------------------


class TestAcceptEvent:
    def test_accepts_message_out_xmpp(self):
        adapter, _, _ = _make_adapter()
        evt = MessageOut(
            target_origin="xmpp",
            channel_id="111",
            author_id="u1",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        assert adapter.accept_event("discord", evt) is True

    def test_rejects_message_out_other_origin(self):
        adapter, _, _ = _make_adapter()
        evt = MessageOut(
            target_origin="irc",
            channel_id="111",
            author_id="u1",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        assert adapter.accept_event("discord", evt) is False

    def test_accepts_message_delete_out_xmpp(self):
        adapter, _, _ = _make_adapter()
        evt = MessageDeleteOut(target_origin="xmpp", channel_id="111", message_id="m1")
        assert adapter.accept_event("discord", evt) is True

    def test_rejects_message_delete_out_other_origin(self):
        adapter, _, _ = _make_adapter()
        evt = MessageDeleteOut(target_origin="discord", channel_id="111", message_id="m1")
        assert adapter.accept_event("discord", evt) is False

    def test_accepts_reaction_out_xmpp(self):
        adapter, _, _ = _make_adapter()
        evt = ReactionOut(
            target_origin="xmpp",
            channel_id="111",
            message_id="m1",
            emoji="👍",
            author_id="u1",
            author_display="U",
        )
        assert adapter.accept_event("discord", evt) is True

    def test_rejects_reaction_out_other_origin(self):
        adapter, _, _ = _make_adapter()
        evt = ReactionOut(
            target_origin="irc",
            channel_id="111",
            message_id="m1",
            emoji="👍",
            author_id="u1",
            author_display="U",
        )
        assert adapter.accept_event("discord", evt) is False

    def test_rejects_unknown_event(self):
        adapter, _, _ = _make_adapter()
        assert adapter.accept_event("discord", object()) is False


# ---------------------------------------------------------------------------
# push_event
# ---------------------------------------------------------------------------


class TestPushEvent:
    def test_queues_message_out(self):
        adapter, _, _ = _make_adapter()
        evt = MessageOut(
            target_origin="xmpp",
            channel_id="111",
            author_id="u1",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        adapter.push_event("discord", evt)
        assert adapter._outbound.qsize() == 1

    def test_queues_message_delete_out(self):
        adapter, _, _ = _make_adapter()
        evt = MessageDeleteOut(target_origin="xmpp", channel_id="111", message_id="m1")
        adapter.push_event("discord", evt)
        assert adapter._outbound.qsize() == 1

    def test_queues_reaction_out(self):
        adapter, _, _ = _make_adapter()
        evt = ReactionOut(
            target_origin="xmpp",
            channel_id="111",
            message_id="m1",
            emoji="👍",
            author_id="u1",
            author_display="U",
        )
        adapter.push_event("discord", evt)
        assert adapter._outbound.qsize() == 1

    def test_ignores_unknown_event(self):
        adapter, _, _ = _make_adapter()
        adapter.push_event("discord", object())
        assert adapter._outbound.qsize() == 0


# ---------------------------------------------------------------------------
# _handle_delete_out
# ---------------------------------------------------------------------------


class TestHandleDeleteOut:
    @pytest.mark.asyncio
    async def test_no_component_returns_early(self):
        adapter, _, router = _make_adapter()
        router.get_mapping_for_discord.return_value = _xmpp_mapping()
        evt = MessageDeleteOut(target_origin="xmpp", channel_id="111", message_id="m1", author_id="u1")
        # _component is None by default
        await adapter._handle_delete_out(evt)
        # identity should never be consulted when component is absent
        cast(MagicMock, adapter._identity).discord_to_xmpp.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_mapping_returns_early(self):
        adapter, _, router = _make_adapter()
        adapter._component = _mock_component()
        router.get_mapping_for_discord.return_value = None
        evt = MessageDeleteOut(target_origin="xmpp", channel_id="111", message_id="m1", author_id="u1")
        await adapter._handle_delete_out(evt)
        adapter._component.send_retraction_as_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_xmpp_msgid_skips_retraction(self):
        adapter, _, router = _make_adapter()
        comp = _mock_component(xmpp_id_for=None)
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()
        evt = MessageDeleteOut(target_origin="xmpp", channel_id="111", message_id="m1", author_id="u1")
        await adapter._handle_delete_out(evt)
        comp.send_retraction_as_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_retraction_with_identity_nick(self):
        adapter, _, router = _make_adapter(identity_nick="xmpp_nick")
        comp = _mock_component()
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()
        evt = MessageDeleteOut(target_origin="xmpp", channel_id="111", message_id="m1", author_id="u1")
        await adapter._handle_delete_out(evt)
        comp.send_retraction_as_user.assert_awaited_once_with("u1", "room@conf.example.com", "xmpp-msg-1", "xmpp_nick")

    @pytest.mark.asyncio
    async def test_sends_retraction_with_fallback_nick(self):
        adapter, _, router = _make_adapter(identity_nick=None)
        comp = _mock_component()
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()
        evt = MessageDeleteOut(target_origin="xmpp", channel_id="111", message_id="m1", author_id="u1")
        await adapter._handle_delete_out(evt)
        comp.send_retraction_as_user.assert_awaited_once_with("u1", "room@conf.example.com", "xmpp-msg-1", "u1")

    @pytest.mark.asyncio
    async def test_sends_retraction_with_no_author_id(self):
        adapter, _, router = _make_adapter(identity_nick=None)
        comp = _mock_component()
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()
        evt = MessageDeleteOut(target_origin="xmpp", channel_id="111", message_id="m1", author_id="")
        await adapter._handle_delete_out(evt)
        comp.send_retraction_as_user.assert_awaited_once_with(
            "unknown", "room@conf.example.com", "xmpp-msg-1", "bridge"
        )


# ---------------------------------------------------------------------------
# _handle_reaction_out
# ---------------------------------------------------------------------------


class TestHandleReactionOut:
    @pytest.mark.asyncio
    async def test_no_component_returns_early(self):
        adapter, _, router = _make_adapter()
        router.get_mapping_for_discord.return_value = _xmpp_mapping()
        evt = ReactionOut(
            target_origin="xmpp",
            channel_id="111",
            message_id="m1",
            emoji="👍",
            author_id="u1",
            author_display="User",
        )
        await adapter._handle_reaction_out(evt)
        cast(MagicMock, adapter._identity).discord_to_xmpp.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_mapping_returns_early(self):
        adapter, _, router = _make_adapter()
        adapter._component = _mock_component()
        router.get_mapping_for_discord.return_value = None
        evt = ReactionOut(
            target_origin="xmpp",
            channel_id="111",
            message_id="m1",
            emoji="👍",
            author_id="u1",
            author_display="User",
        )
        await adapter._handle_reaction_out(evt)
        adapter._component.send_reaction_as_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_xmpp_msgid_skips_reaction(self):
        adapter, _, router = _make_adapter()
        comp = _mock_component(xmpp_id_for=None)
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()
        evt = ReactionOut(
            target_origin="xmpp",
            channel_id="111",
            message_id="m1",
            emoji="👍",
            author_id="u1",
            author_display="User",
        )
        await adapter._handle_reaction_out(evt)
        comp.send_reaction_as_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_reaction_with_identity_nick(self):
        adapter, _, router = _make_adapter(identity_nick="xmpp_nick")
        comp = _mock_component()
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()
        evt = ReactionOut(
            target_origin="xmpp",
            channel_id="111",
            message_id="m1",
            emoji="👍",
            author_id="u1",
            author_display="User",
        )
        await adapter._handle_reaction_out(evt)
        comp.send_reaction_as_user.assert_awaited_once_with(
            "u1", "room@conf.example.com", "xmpp-msg-1", "👍", "xmpp_nick", is_remove=False
        )

    @pytest.mark.asyncio
    async def test_sends_reaction_with_display_fallback(self):
        """When identity returns None, use author_id then author_display as nick."""
        adapter, _, router = _make_adapter(identity_nick=None)
        comp = _mock_component()
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()
        evt = ReactionOut(
            target_origin="xmpp",
            channel_id="111",
            message_id="m1",
            emoji="👍",
            author_id="u1",
            author_display="DisplayUser",
        )
        await adapter._handle_reaction_out(evt)
        comp.send_reaction_as_user.assert_awaited_once_with(
            "u1", "room@conf.example.com", "xmpp-msg-1", "👍", "u1", is_remove=False
        )

    @pytest.mark.asyncio
    async def test_sends_reaction_with_bridge_fallback_no_display(self):
        adapter, _, router = _make_adapter(identity_nick=None)
        comp = _mock_component()
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()
        evt = ReactionOut(
            target_origin="xmpp",
            channel_id="111",
            message_id="m1",
            emoji="👍",
            author_id="",
            author_display="",
        )
        await adapter._handle_reaction_out(evt)
        comp.send_reaction_as_user.assert_awaited_once_with(
            "unknown", "room@conf.example.com", "xmpp-msg-1", "👍", "bridge", is_remove=False
        )


# ---------------------------------------------------------------------------
# _outbound_consumer
# ---------------------------------------------------------------------------


async def _run_consumer_once(adapter: XMPPAdapter, evt: MessageOut | MessageDeleteOut | ReactionOut) -> None:
    """Put one event in the queue, run consumer until queue is drained, then cancel."""
    adapter._outbound.put_nowait(evt)
    task = asyncio.create_task(adapter._outbound_consumer())
    # Wait until queue is empty
    for _ in range(50):
        await asyncio.sleep(0.05)
        if adapter._outbound.empty():
            break
    task.cancel()
    import contextlib

    with contextlib.suppress(asyncio.CancelledError):
        await task


class TestOutboundConsumer:
    @pytest.mark.asyncio
    async def test_normal_message_send(self):
        adapter, _, router = _make_adapter(identity_nick="xmpp_nick")
        comp = _mock_component()
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()

        evt = MessageOut(
            target_origin="xmpp",
            channel_id="111",
            author_id="u1",
            author_display="U",
            content="hello",
            message_id="m1",
        )
        await _run_consumer_once(adapter, evt)

        comp.send_message_as_user.assert_awaited_once_with(
            "u1",
            "room@conf.example.com",
            "hello",
            "xmpp_nick",
            reply_to_id=None,
            discord_message_id="m1",
        )

    @pytest.mark.asyncio
    async def test_message_with_avatar_sets_avatar(self):
        adapter, _, router = _make_adapter(identity_nick="xmpp_nick")
        comp = _mock_component()
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()

        evt = MessageOut(
            target_origin="xmpp",
            channel_id="111",
            author_id="u1",
            author_display="U",
            content="hi",
            message_id="m1",
            avatar_url="https://cdn.example.com/avatar.png",
        )
        await _run_consumer_once(adapter, evt)

        comp.set_avatar_for_user.assert_awaited_once_with("u1", "xmpp_nick", "https://cdn.example.com/avatar.png")

    @pytest.mark.asyncio
    async def test_message_no_identity_nick_uses_author_id_fallback(self):
        adapter, _, router = _make_adapter(identity_nick=None)
        comp = _mock_component()
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()

        evt = MessageOut(
            target_origin="xmpp",
            channel_id="111",
            author_id="u1",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        await _run_consumer_once(adapter, evt)

        comp.send_message_as_user.assert_awaited_once_with(
            "u1",
            "room@conf.example.com",
            "hi",
            "u1",
            reply_to_id=None,
            discord_message_id="m1",
        )

    @pytest.mark.asyncio
    async def test_edit_with_known_xmpp_id_sends_correction(self):
        adapter, _, router = _make_adapter(identity_nick="xmpp_nick")
        comp = _mock_component(xmpp_id_for="xmpp-orig-id")
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()

        evt = MessageOut(
            target_origin="xmpp",
            channel_id="111",
            author_id="u1",
            author_display="U",
            content="edited",
            message_id="m1",
            raw={"is_edit": True},
        )
        await _run_consumer_once(adapter, evt)

        comp.send_correction_as_user.assert_awaited_once_with(
            "u1", "room@conf.example.com", "edited", "xmpp_nick", "xmpp-orig-id"
        )
        comp.send_message_as_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_edit_with_unknown_xmpp_id_skips_correction(self):
        adapter, _, router = _make_adapter(identity_nick="xmpp_nick")
        comp = _mock_component(xmpp_id_for=None)
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()

        evt = MessageOut(
            target_origin="xmpp",
            channel_id="111",
            author_id="u1",
            author_display="U",
            content="edited",
            message_id="m1",
            raw={"is_edit": True},
        )
        await _run_consumer_once(adapter, evt)

        comp.send_correction_as_user.assert_not_called()
        comp.send_message_as_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_reply_passes_xmpp_reply_id(self):
        adapter, _, router = _make_adapter(identity_nick="xmpp_nick")
        comp = _mock_component(xmpp_id_for="xmpp-reply-target")
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()

        evt = MessageOut(
            target_origin="xmpp",
            channel_id="111",
            author_id="u1",
            author_display="U",
            content="reply",
            message_id="m2",
            reply_to_id="m1",
        )
        await _run_consumer_once(adapter, evt)

        comp.send_message_as_user.assert_awaited_once_with(
            "u1",
            "room@conf.example.com",
            "reply",
            "xmpp_nick",
            reply_to_id="xmpp-reply-target",
            discord_message_id="m2",
        )

    @pytest.mark.asyncio
    async def test_no_mapping_skips_send(self):
        adapter, _, router = _make_adapter()
        comp = _mock_component()
        adapter._component = comp
        router.get_mapping_for_discord.return_value = None

        evt = MessageOut(
            target_origin="xmpp",
            channel_id="999",
            author_id="u1",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        await _run_consumer_once(adapter, evt)

        comp.send_message_as_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_out_dispatched_to_handle_delete(self):
        adapter, _, router = _make_adapter(identity_nick="xmpp_nick")
        comp = _mock_component()
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()

        evt = MessageDeleteOut(target_origin="xmpp", channel_id="111", message_id="m1", author_id="u1")
        await _run_consumer_once(adapter, evt)

        comp.send_retraction_as_user.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reaction_out_dispatched_to_handle_reaction(self):
        adapter, _, router = _make_adapter(identity_nick="xmpp_nick")
        comp = _mock_component()
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()

        evt = ReactionOut(
            target_origin="xmpp",
            channel_id="111",
            message_id="m1",
            emoji="❤️",
            author_id="u1",
            author_display="U",
        )
        await _run_consumer_once(adapter, evt)

        comp.send_reaction_as_user.assert_awaited_once()


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------


class TestStart:
    @pytest.mark.asyncio
    async def test_start_missing_jid_returns_early(self):
        adapter, bus, _ = _make_adapter()
        with patch.dict("os.environ", {}, clear=True):
            await adapter.start()
        bus.register.assert_not_called()
        assert adapter._component is None

    @pytest.mark.asyncio
    async def test_start_missing_secret_returns_early(self):
        adapter, bus, _ = _make_adapter()
        env = {"BRIDGE_XMPP_COMPONENT_JID": "bridge.example.com"}
        with patch.dict("os.environ", env, clear=True):
            await adapter.start()
        bus.register.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_missing_server_returns_early(self):
        adapter, bus, _ = _make_adapter()
        env = {
            "BRIDGE_XMPP_COMPONENT_JID": "bridge.example.com",
            "BRIDGE_XMPP_COMPONENT_SECRET": "s3cr3t",
        }
        with patch.dict("os.environ", env, clear=True):
            await adapter.start()
        bus.register.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_without_identity_succeeds_dev_mode(self):
        """XMPP adapter starts without Portal (dev mode); uses fallback nicks."""
        bus = MagicMock(spec=Bus)
        router = MagicMock(spec=ChannelRouter)
        router.all_mappings.return_value = [_xmpp_mapping()]
        adapter = XMPPAdapter(bus, router, identity_resolver=None)
        mock_comp = MagicMock()
        mock_comp.connect = MagicMock(return_value=asyncio.Future())
        env = {
            "BRIDGE_XMPP_COMPONENT_JID": "bridge.example.com",
            "BRIDGE_XMPP_COMPONENT_SECRET": "s3cr3t",
            "BRIDGE_XMPP_COMPONENT_SERVER": "localhost",
        }
        with (
            patch.dict("os.environ", env, clear=True),
            patch("bridge.adapters.xmpp.XMPPComponent", return_value=mock_comp),
        ):
            await adapter.start()
        bus.register.assert_called_once_with(adapter)
        assert adapter._component is mock_comp
        # Cleanup
        if adapter._consumer_task:
            adapter._consumer_task.cancel()
        if adapter._component_task:
            adapter._component_task.cancel()

    @pytest.mark.asyncio
    async def test_start_no_xmpp_mappings_returns_early(self):
        adapter, bus, router = _make_adapter()
        # Mapping with no xmpp target
        router.all_mappings.return_value = [ChannelMapping(discord_channel_id="111", irc=None, xmpp=None)]
        env = {
            "BRIDGE_XMPP_COMPONENT_JID": "bridge.example.com",
            "BRIDGE_XMPP_COMPONENT_SECRET": "s3cr3t",
            "BRIDGE_XMPP_COMPONENT_SERVER": "localhost",
        }
        with patch.dict("os.environ", env, clear=True):
            await adapter.start()
        bus.register.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_success_registers_and_creates_tasks(self):
        adapter, bus, _router = _make_adapter(mappings=[_xmpp_mapping()])
        env = {
            "BRIDGE_XMPP_COMPONENT_JID": "bridge.example.com",
            "BRIDGE_XMPP_COMPONENT_SECRET": "s3cr3t",
            "BRIDGE_XMPP_COMPONENT_SERVER": "localhost",
        }
        mock_comp = MagicMock()
        mock_comp.connect = MagicMock(return_value=asyncio.Future())

        with (
            patch.dict("os.environ", env, clear=True),
            patch("bridge.adapters.xmpp.XMPPComponent", return_value=mock_comp),
        ):
            await adapter.start()

        bus.register.assert_called_once_with(adapter)
        assert adapter._component is mock_comp
        assert adapter._consumer_task is not None
        assert adapter._component_task is not None

        # Cleanup
        adapter._consumer_task.cancel()
        adapter._component_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await adapter._consumer_task
        with pytest.raises(asyncio.CancelledError):
            await adapter._component_task


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------


class TestStop:
    @pytest.mark.asyncio
    async def test_stop_cancels_tasks_and_disconnects(self):
        adapter, bus, _ = _make_adapter()
        comp = _mock_component()
        adapter._component = comp

        # Create real tasks that block forever
        adapter._consumer_task = asyncio.create_task(asyncio.sleep(9999))
        adapter._component_task = asyncio.create_task(asyncio.sleep(9999))

        await adapter.stop()

        bus.unregister.assert_called_once_with(adapter)
        comp.disconnect.assert_called_once()
        assert adapter._component is None
        assert adapter._component_task is None

    @pytest.mark.asyncio
    async def test_stop_with_no_tasks_is_safe(self):
        adapter, bus, _ = _make_adapter()
        await adapter.stop()
        bus.unregister.assert_called_once_with(adapter)


# ---------------------------------------------------------------------------
# Edge cases / race conditions
# ---------------------------------------------------------------------------


class TestEdgeCases:
    # --- XMPPAdapter: no identity resolver ---

    @pytest.mark.asyncio
    async def test_handle_delete_out_no_identity_uses_fallback_nick(self):
        """Without identity resolver (dev mode), delete uses author_id as nick."""
        bus = MagicMock(spec=Bus)
        router = MagicMock(spec=ChannelRouter)
        adapter = XMPPAdapter(bus, router, identity_resolver=None)
        comp = _mock_component()
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()
        evt = MessageDeleteOut(target_origin="xmpp", channel_id="111", message_id="m1", author_id="u1")
        await adapter._handle_delete_out(evt)
        comp.send_retraction_as_user.assert_awaited_once_with("u1", "room@conf.example.com", "xmpp-msg-1", "u1")

    @pytest.mark.asyncio
    async def test_handle_reaction_out_no_identity_uses_fallback_nick(self):
        """Without identity resolver (dev mode), reaction uses author_id as nick."""
        bus = MagicMock(spec=Bus)
        router = MagicMock(spec=ChannelRouter)
        adapter = XMPPAdapter(bus, router, identity_resolver=None)
        comp = _mock_component()
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()
        evt = ReactionOut(
            target_origin="xmpp",
            channel_id="111",
            message_id="m1",
            emoji="👍",
            author_id="u1",
            author_display="U",
        )
        await adapter._handle_reaction_out(evt)
        comp.send_reaction_as_user.assert_awaited_once_with(
            "u1", "room@conf.example.com", "xmpp-msg-1", "👍", "u1", is_remove=False
        )

    # --- Consumer: exception during send doesn't crash loop ---

    @pytest.mark.asyncio
    async def test_consumer_continues_after_send_exception(self):
        adapter, _, router = _make_adapter(identity_nick="nick")
        comp = _mock_component()
        comp.send_message_as_user = AsyncMock(side_effect=[OSError("fail"), "xmpp-id-2"])
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()

        evt1 = MessageOut(
            target_origin="xmpp",
            channel_id="111",
            author_id="u1",
            author_display="U",
            content="first",
            message_id="m1",
        )
        evt2 = MessageOut(
            target_origin="xmpp",
            channel_id="111",
            author_id="u1",
            author_display="U",
            content="second",
            message_id="m2",
        )
        adapter._outbound.put_nowait(evt1)
        adapter._outbound.put_nowait(evt2)

        task = asyncio.create_task(adapter._outbound_consumer())
        for _ in range(100):
            await asyncio.sleep(0.05)
            if adapter._outbound.empty():
                break
        task.cancel()
        import contextlib

        with contextlib.suppress(asyncio.CancelledError):
            await task

        # Second message was still attempted despite first failing
        assert comp.send_message_as_user.await_count == 2

    # --- push_event after stop: queue accepts but no crash ---

    def test_push_event_after_stop_does_not_raise(self):
        adapter, _, _ = _make_adapter()
        # No consumer running, but push should not raise
        evt = MessageOut(
            target_origin="xmpp",
            channel_id="111",
            author_id="u1",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        adapter.push_event("discord", evt)
        assert adapter._outbound.qsize() == 1

    # --- start() called twice: second call replaces component ---

    @pytest.mark.asyncio
    async def test_start_twice_replaces_component(self):
        adapter, _bus, _router = _make_adapter(mappings=[_xmpp_mapping()])
        env = {
            "BRIDGE_XMPP_COMPONENT_JID": "bridge.example.com",
            "BRIDGE_XMPP_COMPONENT_SECRET": "s3cr3t",
            "BRIDGE_XMPP_COMPONENT_SERVER": "localhost",
        }
        comp1, comp2 = MagicMock(), MagicMock()
        comp1.connect = MagicMock(return_value=asyncio.Future())
        comp2.connect = MagicMock(return_value=asyncio.Future())
        components = [comp1, comp2]

        with (
            patch.dict("os.environ", env, clear=True),
            patch("bridge.adapters.xmpp.XMPPComponent", side_effect=components),
        ):
            await adapter.start()
            first_task = adapter._consumer_task
            await adapter.start()

        # Component was replaced
        assert adapter._component is comp2
        # Cleanup old tasks
        if first_task:
            first_task.cancel()
        if adapter._consumer_task:
            adapter._consumer_task.cancel()
        if adapter._component_task:
            adapter._component_task.cancel()

    # --- Consumer: no component set (component is None) ---

    @pytest.mark.asyncio
    async def test_consumer_skips_when_no_component(self):
        adapter, _, router = _make_adapter(identity_nick="nick")
        # _component stays None
        router.get_mapping_for_discord.return_value = _xmpp_mapping()

        evt = MessageOut(
            target_origin="xmpp",
            channel_id="111",
            author_id="u1",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        await _run_consumer_once(adapter, evt)
        # identity should never be consulted when component is absent
        cast(MagicMock, adapter._identity).discord_to_xmpp.assert_not_called()

    # --- Outbound consumer: xmpp_msg_id is None (send returns None) ---

    @pytest.mark.asyncio
    async def test_consumer_handles_none_xmpp_msg_id(self):
        adapter, _, router = _make_adapter(identity_nick="nick")
        comp = _mock_component()
        comp.send_message_as_user = AsyncMock(return_value=None)
        adapter._component = comp
        router.get_mapping_for_discord.return_value = _xmpp_mapping()

        evt = MessageOut(
            target_origin="xmpp",
            channel_id="111",
            author_id="u1",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        await _run_consumer_once(adapter, evt)

        # store should NOT be called when xmpp_msg_id is None
        comp._msgid_tracker.store.assert_not_called()


# ---------------------------------------------------------------------------
# _outbound_consumer: mapping exists but xmpp leg absent (line 63 guard)
# ---------------------------------------------------------------------------


class TestConsumerGuardConditions:
    @pytest.mark.asyncio
    async def test_consumer_skips_when_mapping_has_no_xmpp_target(self):
        """mapping exists but mapping.xmpp is None → guard on line 63 fails."""
        from bridge.gateway.router import IrcTarget

        adapter, _, router = _make_adapter(identity_nick="nick")
        comp = _mock_component()
        adapter._component = comp
        # Mapping with IRC only, no XMPP
        irc_only = ChannelMapping(
            discord_channel_id="111",
            irc=IrcTarget(server="s", port=6667, tls=False, channel="#c"),
            xmpp=None,
        )
        router.get_mapping_for_discord.return_value = irc_only

        evt = MessageOut(
            target_origin="xmpp",
            channel_id="111",
            author_id="u1",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        await _run_consumer_once(adapter, evt)
        comp.send_message_as_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_consumer_uses_fallback_nick_when_no_identity(self):
        """_identity is None (dev mode) → use author_id as fallback nick."""
        adapter = XMPPAdapter(MagicMock(spec=Bus), MagicMock(spec=ChannelRouter), None)
        comp = _mock_component()
        adapter._component = comp
        router = adapter._router
        router.get_mapping_for_discord.return_value = _xmpp_mapping()  # type: ignore[attr-defined]

        evt = MessageOut(
            target_origin="xmpp",
            channel_id="111",
            author_id="u1",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        await _run_consumer_once(adapter, evt)
        comp.send_message_as_user.assert_awaited_once_with(
            "u1",
            "room@conf.example.com",
            "hi",
            "u1",
            reply_to_id=None,
            discord_message_id="m1",
        )
