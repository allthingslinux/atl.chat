"""Tests for IRCAdapter (bridge/adapters/irc.py)."""

from __future__ import annotations

import asyncio
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bridge.adapters.irc import IRCAdapter
from bridge.events import MessageDeleteOut, MessageOut, ReactionOut, TypingOut
from bridge.gateway import Bus, ChannelRouter
from bridge.gateway.router import ChannelMapping, IrcTarget

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_adapter(
    identity_nick: str | None = "irc_nick",
) -> tuple[IRCAdapter, MagicMock, MagicMock]:
    bus = MagicMock(spec=Bus)
    router = MagicMock(spec=ChannelRouter)
    identity = AsyncMock()
    identity.discord_to_irc = AsyncMock(return_value=identity_nick)
    identity.has_irc = AsyncMock(return_value=True)
    adapter = IRCAdapter(bus, router, identity_resolver=identity)
    return adapter, bus, router


def _close_coro(coro: object) -> MagicMock:
    """Close a coroutine passed to a mocked create_task to suppress RuntimeWarning."""
    import inspect

    if inspect.iscoroutine(coro):
        coro.close()
    return MagicMock()


def _irc_mapping(discord_id: str = "111", channel: str = "#test") -> ChannelMapping:
    return ChannelMapping(
        discord_channel_id=discord_id,
        irc=IrcTarget(server="irc.libera.chat", port=6697, tls=True, channel=channel),
        xmpp=None,
    )


def _mock_client() -> MagicMock:
    c = MagicMock()
    c.rawmsg = AsyncMock()
    c.queue_message = MagicMock()
    c._typing_last = 0
    return c


# ---------------------------------------------------------------------------
# accept_event
# ---------------------------------------------------------------------------


class TestAcceptEvent:
    def test_accepts_message_out_irc(self):
        adapter, _, _ = _make_adapter()
        evt = MessageOut(
            target_origin="irc",
            channel_id="111",
            author_id="u",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        assert adapter.accept_event("discord", evt) is True

    def test_rejects_message_out_other(self):
        adapter, _, _ = _make_adapter()
        evt = MessageOut(
            target_origin="xmpp",
            channel_id="111",
            author_id="u",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        assert adapter.accept_event("discord", evt) is False

    def test_accepts_message_delete_out_irc(self):
        adapter, _, _ = _make_adapter()
        evt = MessageDeleteOut(target_origin="irc", channel_id="111", message_id="m1")
        assert adapter.accept_event("discord", evt) is True

    def test_rejects_message_delete_out_other(self):
        adapter, _, _ = _make_adapter()
        evt = MessageDeleteOut(target_origin="xmpp", channel_id="111", message_id="m1")
        assert adapter.accept_event("discord", evt) is False

    def test_accepts_reaction_out_irc(self):
        adapter, _, _ = _make_adapter()
        evt = ReactionOut(
            target_origin="irc",
            channel_id="111",
            message_id="m1",
            emoji="👍",
            author_id="u",
            author_display="U",
        )
        assert adapter.accept_event("discord", evt) is True

    def test_rejects_reaction_out_other(self):
        adapter, _, _ = _make_adapter()
        evt = ReactionOut(
            target_origin="xmpp",
            channel_id="111",
            message_id="m1",
            emoji="👍",
            author_id="u",
            author_display="U",
        )
        assert adapter.accept_event("discord", evt) is False

    def test_accepts_typing_out_irc(self):
        adapter, _, _ = _make_adapter()
        evt = TypingOut(target_origin="irc", channel_id="111")
        assert adapter.accept_event("discord", evt) is True

    def test_rejects_typing_out_other(self):
        adapter, _, _ = _make_adapter()
        evt = TypingOut(target_origin="xmpp", channel_id="111")
        assert adapter.accept_event("discord", evt) is False

    def test_rejects_unknown_event(self):
        adapter, _, _ = _make_adapter()
        assert adapter.accept_event("discord", object()) is False


# ---------------------------------------------------------------------------
# push_event
# ---------------------------------------------------------------------------


class TestPushEvent:
    def test_message_delete_out_creates_task_when_client_present(self):
        adapter, _, _ = _make_adapter()
        adapter._client = _mock_client()
        evt = MessageDeleteOut(target_origin="irc", channel_id="111", message_id="m1")
        with patch("asyncio.create_task", side_effect=_close_coro) as mock_task:
            adapter.push_event("discord", evt)
            mock_task.assert_called_once()

    def test_message_delete_out_skips_when_no_client(self):
        adapter, _, _ = _make_adapter()
        evt = MessageDeleteOut(target_origin="irc", channel_id="111", message_id="m1")
        with patch("asyncio.create_task", side_effect=_close_coro) as mock_task:
            adapter.push_event("discord", evt)
            mock_task.assert_not_called()

    def test_reaction_out_creates_task_when_client_present(self):
        adapter, _, _ = _make_adapter()
        adapter._client = _mock_client()
        evt = ReactionOut(
            target_origin="irc",
            channel_id="111",
            message_id="m1",
            emoji="👍",
            author_id="u",
            author_display="U",
        )
        with patch("asyncio.create_task", side_effect=_close_coro) as mock_task:
            adapter.push_event("discord", evt)
            mock_task.assert_called_once()

    def test_typing_out_creates_task_when_client_present(self):
        adapter, _, _ = _make_adapter()
        adapter._client = _mock_client()
        evt = TypingOut(target_origin="irc", channel_id="111")
        with patch("asyncio.create_task", side_effect=_close_coro) as mock_task:
            adapter.push_event("discord", evt)
            mock_task.assert_called_once()

    def test_message_out_queues_via_client_when_no_puppet_manager(self):
        adapter, _, _ = _make_adapter()
        adapter._client = _mock_client()
        adapter._puppet_manager = None
        evt = MessageOut(
            target_origin="irc",
            channel_id="111",
            author_id="u",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        adapter.push_event("discord", evt)
        cast(MagicMock, adapter._client).queue_message.assert_called_once_with(evt)

    def test_message_out_uses_puppet_when_puppet_manager_present(self):
        adapter, _, _ = _make_adapter()
        adapter._client = _mock_client()
        adapter._puppet_manager = MagicMock()
        evt = MessageOut(
            target_origin="irc",
            channel_id="111",
            author_id="u",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        with patch("asyncio.create_task", side_effect=_close_coro) as mock_task:
            adapter.push_event("discord", evt)
            mock_task.assert_called_once()
        cast(MagicMock, adapter._client).queue_message.assert_not_called()


# ---------------------------------------------------------------------------
# _send_reaction
# ---------------------------------------------------------------------------


class TestSendReaction:
    @pytest.mark.asyncio
    async def test_no_client_returns_early(self):
        adapter, _, router = _make_adapter()
        router.get_mapping_for_discord.return_value = _irc_mapping()
        evt = ReactionOut(
            target_origin="irc",
            channel_id="111",
            message_id="m1",
            emoji="👍",
            author_id="u",
            author_display="U",
        )
        await adapter._send_reaction(evt)  # no error

    @pytest.mark.asyncio
    async def test_no_irc_msgid_skips(self):
        adapter, _, router = _make_adapter()
        adapter._client = _mock_client()
        router.get_mapping_for_discord.return_value = _irc_mapping()
        evt = ReactionOut(
            target_origin="irc",
            channel_id="111",
            message_id="unknown",
            emoji="👍",
            author_id="u",
            author_display="U",
        )
        await adapter._send_reaction(evt)
        adapter._client.rawmsg.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_mapping_skips(self):
        adapter, _, router = _make_adapter()
        adapter._client = _mock_client()
        adapter._msgid_tracker.store("irc-id", "discord-id")
        router.get_mapping_for_discord.return_value = None
        evt = ReactionOut(
            target_origin="irc",
            channel_id="111",
            message_id="discord-id",
            emoji="👍",
            author_id="u",
            author_display="U",
        )
        await adapter._send_reaction(evt)
        adapter._client.rawmsg.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_tagmsg_with_react(self):
        adapter, _, router = _make_adapter()
        adapter._client = _mock_client()
        adapter._msgid_tracker.store("irc-id", "discord-id")
        router.get_mapping_for_discord.return_value = _irc_mapping()
        evt = ReactionOut(
            target_origin="irc",
            channel_id="111",
            message_id="discord-id",
            emoji="👍",
            author_id="u",
            author_display="U",
        )
        await adapter._send_reaction(evt)
        adapter._client.rawmsg.assert_awaited_once_with(
            "TAGMSG",
            "#test",
            tags={"+draft/reply": "irc-id", "+draft/react": "👍"},
        )


# ---------------------------------------------------------------------------
# _send_typing
# ---------------------------------------------------------------------------


class TestSendTyping:
    @pytest.mark.asyncio
    async def test_no_client_returns_early(self):
        adapter, _, _ = _make_adapter()
        evt = TypingOut(target_origin="irc", channel_id="111")
        await adapter._send_typing(evt)  # no error

    @pytest.mark.asyncio
    async def test_throttled_within_3s(self):
        import time

        adapter, _, router = _make_adapter()
        adapter._client = _mock_client()
        adapter._client._typing_last = time.time()  # just sent
        router.get_mapping_for_discord.return_value = _irc_mapping()
        evt = TypingOut(target_origin="irc", channel_id="111")
        await adapter._send_typing(evt)
        adapter._client.rawmsg.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_typing_tagmsg(self):
        adapter, _, router = _make_adapter()
        adapter._client = _mock_client()
        adapter._client._typing_last = 0
        router.get_mapping_for_discord.return_value = _irc_mapping()
        evt = TypingOut(target_origin="irc", channel_id="111")
        await adapter._send_typing(evt)
        adapter._client.rawmsg.assert_awaited_once_with(
            "TAGMSG", "#test", tags={"typing": "active"}
        )

    @pytest.mark.asyncio
    async def test_no_mapping_skips(self):
        adapter, _, router = _make_adapter()
        adapter._client = _mock_client()
        adapter._client._typing_last = 0
        router.get_mapping_for_discord.return_value = None
        evt = TypingOut(target_origin="irc", channel_id="111")
        await adapter._send_typing(evt)
        adapter._client.rawmsg.assert_not_called()


# ---------------------------------------------------------------------------
# _send_redact
# ---------------------------------------------------------------------------


class TestSendRedact:
    @pytest.mark.asyncio
    async def test_no_client_returns_early(self):
        adapter, _, _ = _make_adapter()
        evt = MessageDeleteOut(target_origin="irc", channel_id="111", message_id="m1")
        await adapter._send_redact(evt)  # no error

    @pytest.mark.asyncio
    async def test_no_irc_msgid_skips(self):
        adapter, _, router = _make_adapter()
        adapter._client = _mock_client()
        router.get_mapping_for_discord.return_value = _irc_mapping()
        evt = MessageDeleteOut(target_origin="irc", channel_id="111", message_id="unknown")
        await adapter._send_redact(evt)
        adapter._client.rawmsg.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_mapping_skips(self):
        adapter, _, router = _make_adapter()
        adapter._client = _mock_client()
        adapter._msgid_tracker.store("irc-id", "discord-id")
        router.get_mapping_for_discord.return_value = None
        evt = MessageDeleteOut(target_origin="irc", channel_id="111", message_id="discord-id")
        await adapter._send_redact(evt)
        adapter._client.rawmsg.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_redact(self):
        adapter, _, router = _make_adapter()
        adapter._client = _mock_client()
        adapter._msgid_tracker.store("irc-id", "discord-id")
        router.get_mapping_for_discord.return_value = _irc_mapping()
        evt = MessageDeleteOut(target_origin="irc", channel_id="111", message_id="discord-id")
        await adapter._send_redact(evt)
        adapter._client.rawmsg.assert_awaited_once_with("REDACT", "#test", "irc-id")


# ---------------------------------------------------------------------------
# _send_via_puppet
# ---------------------------------------------------------------------------


class TestSendViaPuppet:
    @pytest.mark.asyncio
    async def test_no_puppet_manager_returns_early(self):
        adapter, _, _ = _make_adapter()
        adapter._puppet_manager = None
        evt = MessageOut(
            target_origin="irc",
            channel_id="111",
            author_id="u",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        await adapter._send_via_puppet(evt)  # no error

    @pytest.mark.asyncio
    async def test_no_mapping_returns_early(self):
        adapter, _, router = _make_adapter()
        adapter._puppet_manager = AsyncMock()
        router.get_mapping_for_discord.return_value = None
        evt = MessageOut(
            target_origin="irc",
            channel_id="111",
            author_id="u",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        await adapter._send_via_puppet(evt)
        adapter._puppet_manager.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_via_puppet_when_has_irc(self):
        adapter, _, router = _make_adapter()
        adapter._puppet_manager = AsyncMock()
        assert adapter._identity is not None
        adapter._identity.has_irc = AsyncMock(return_value=True)
        router.get_mapping_for_discord.return_value = _irc_mapping()
        evt = MessageOut(
            target_origin="irc",
            channel_id="111",
            author_id="u",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        await adapter._send_via_puppet(evt)
        adapter._puppet_manager.send_message.assert_awaited_once_with("u", "#test", "hi")

    @pytest.mark.asyncio
    async def test_falls_back_to_client_when_no_irc_identity(self):
        adapter, _, router = _make_adapter()
        adapter._puppet_manager = AsyncMock()
        adapter._client = _mock_client()
        assert adapter._identity is not None
        adapter._identity.has_irc = AsyncMock(return_value=False)
        router.get_mapping_for_discord.return_value = _irc_mapping()
        evt = MessageOut(
            target_origin="irc",
            channel_id="111",
            author_id="u",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        await adapter._send_via_puppet(evt)
        cast(MagicMock, adapter._client).queue_message.assert_called_once_with(evt)


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------


class TestStart:
    @pytest.mark.asyncio
    async def test_no_irc_mappings_returns_early(self):
        adapter, bus, router = _make_adapter()
        router.all_mappings.return_value = [
            ChannelMapping(discord_channel_id="111", irc=None, xmpp=None)
        ]
        await adapter.start()
        bus.register.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_registers_and_creates_task(self):
        adapter, bus, router = _make_adapter()
        router.all_mappings.return_value = [_irc_mapping()]

        mock_puppet_mgr = AsyncMock()
        mock_puppet_mgr.start = AsyncMock()

        async def _fake_backoff(client, hostname, port, tls):
            await asyncio.sleep(9999)

        with (
            patch("bridge.adapters.irc.IRCClient") as mock_irc_client,
            patch("bridge.adapters.irc._connect_with_backoff", side_effect=_fake_backoff),
            patch("bridge.adapters.irc.IRCPuppetManager", return_value=mock_puppet_mgr),
            patch.dict(
                "os.environ", {"BRIDGE_IRC_NICK": "testbot", "IRC_PUPPET_IDLE_TIMEOUT_HOURS": "12"}
            ),
        ):
            mock_irc_client.return_value = MagicMock()
            await adapter.start()

        bus.register.assert_called_once_with(adapter)
        assert adapter._task is not None
        assert adapter._puppet_manager is mock_puppet_mgr

        adapter._task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await adapter._task


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------


class TestStop:
    @pytest.mark.asyncio
    async def test_stop_cleans_up(self):
        adapter, bus, _ = _make_adapter()
        mock_client = AsyncMock()
        mock_puppet_mgr = AsyncMock()
        adapter._client = mock_client
        adapter._puppet_manager = mock_puppet_mgr
        adapter._task = asyncio.create_task(asyncio.sleep(9999))

        await adapter.stop()

        bus.unregister.assert_called_once_with(adapter)
        mock_puppet_mgr.stop.assert_awaited_once()
        mock_client.disconnect.assert_awaited_once()
        assert adapter._client is None
        assert adapter._task is None
        assert adapter._puppet_manager is None

    @pytest.mark.asyncio
    async def test_stop_with_no_client_is_safe(self):
        adapter, bus, _ = _make_adapter()
        await adapter.stop()
        bus.unregister.assert_called_once_with(adapter)


# ---------------------------------------------------------------------------
# Edge cases / race conditions
# ---------------------------------------------------------------------------


class TestIRCAdapterEdgeCases:
    # --- push_event: MessageOut with no client and no puppet manager ---

    def test_push_event_message_out_no_client_no_puppet_does_nothing(self):
        adapter, _, _ = _make_adapter()
        # _client and _puppet_manager are both None by default
        evt = MessageOut(
            target_origin="irc",
            channel_id="111",
            author_id="u",
            author_display="U",
            content="hi",
            message_id="m1",
        )
        adapter.push_event("discord", evt)
        # Nothing queued — no client to send through
        assert adapter._msgid_tracker.get_irc_msgid("m1") is None

    # --- _send_typing: throttle resets after 3+ seconds ---

    @pytest.mark.asyncio
    async def test_send_typing_allowed_after_throttle_expires(self):
        import time

        adapter, _, router = _make_adapter()
        adapter._client = _mock_client()
        adapter._client._typing_last = time.time() - 4  # 4s ago, past 3s throttle
        router.get_mapping_for_discord.return_value = _irc_mapping()
        evt = TypingOut(target_origin="irc", channel_id="111")
        await adapter._send_typing(evt)
        adapter._client.rawmsg.assert_awaited_once()

    # --- stop() called twice: idempotent ---

    @pytest.mark.asyncio
    async def test_stop_twice_is_safe(self):
        adapter, bus, _ = _make_adapter()
        await adapter.stop()
        await adapter.stop()  # second call should not raise
        assert bus.unregister.call_count == 2

    # --- _send_reaction: rawmsg exception is swallowed ---

    @pytest.mark.asyncio
    async def test_send_reaction_exception_does_not_propagate(self):
        adapter, _, router = _make_adapter()
        adapter._client = _mock_client()
        adapter._client.rawmsg = AsyncMock(side_effect=OSError("network error"))
        adapter._msgid_tracker.store("irc-id", "discord-id")
        router.get_mapping_for_discord.return_value = _irc_mapping()
        evt = ReactionOut(
            target_origin="irc",
            channel_id="111",
            message_id="discord-id",
            emoji="👍",
            author_id="u",
            author_display="U",
        )
        await adapter._send_reaction(evt)
        # rawmsg was attempted (exception was swallowed, not silently skipped)
        adapter._client.rawmsg.assert_awaited_once()

    # --- _send_redact: rawmsg exception is swallowed ---

    @pytest.mark.asyncio
    async def test_send_redact_exception_does_not_propagate(self):
        adapter, _, router = _make_adapter()
        adapter._client = _mock_client()
        adapter._client.rawmsg = AsyncMock(side_effect=OSError("network error"))
        adapter._msgid_tracker.store("irc-id", "discord-id")
        router.get_mapping_for_discord.return_value = _irc_mapping()
        evt = MessageDeleteOut(target_origin="irc", channel_id="111", message_id="discord-id")
        await adapter._send_redact(evt)
        # rawmsg was attempted (exception was swallowed, not silently skipped)
        adapter._client.rawmsg.assert_awaited_once()

    # --- Race: _client set to None between push_event check and create_task ---

    def test_push_event_delete_out_no_client_skips_task(self):
        adapter, _, _ = _make_adapter()
        adapter._client = None  # explicitly None
        evt = MessageDeleteOut(target_origin="irc", channel_id="111", message_id="m1")
        with patch("asyncio.create_task", side_effect=_close_coro) as mock_task:
            adapter.push_event("discord", evt)
            mock_task.assert_not_called()
