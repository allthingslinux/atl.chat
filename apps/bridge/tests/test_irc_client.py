"""Tests for IRCClient (bridge/adapters/irc.py)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bridge.adapters.irc import IRCClient, MessageIDTracker, ReactionTracker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(
    server: str = "irc.libera.chat",
    nick: str = "bot",
    channels: list[str] | None = None,
    auto_rejoin: bool = True,
    rejoin_delay: float = 0,
) -> tuple[IRCClient, MagicMock, MagicMock]:
    bus = MagicMock()
    router = MagicMock()
    tracker = MessageIDTracker()
    reaction_tracker = ReactionTracker()
    client = IRCClient(
        bus=bus,
        router=router,
        server=server,
        nick=nick,
        channels=channels or ["#test"],
        msgid_tracker=tracker,
        reaction_tracker=reaction_tracker,
        auto_rejoin=auto_rejoin,
        rejoin_delay=rejoin_delay,
    )
    client._ready = True
    return client, bus, router


def _mock_message(params=None, tags=None, source="user!user@host"):
    msg = MagicMock()
    msg.params = params or []
    msg.tags = tags or {}
    msg.source = source
    return msg


# ---------------------------------------------------------------------------
# on_disconnect
# ---------------------------------------------------------------------------


class TestOnDisconnect:
    @pytest.mark.asyncio
    async def test_sets_ready_false(self):
        client, _, _ = _make_client()
        client._ready = True
        with patch.object(type(client).__mro__[1], "on_disconnect", AsyncMock()):
            await client.on_disconnect(expected=True)
        assert client._ready is False


# ---------------------------------------------------------------------------
# on_raw_pong
# ---------------------------------------------------------------------------


class TestOnRawPong:
    @pytest.mark.asyncio
    async def test_marks_ready_on_ready_pong(self):
        client, _, _ = _make_client()
        client._ready = False
        msg = _mock_message(params=["server", "ready"])
        with patch.object(type(client).__mro__[1], "on_raw_pong", AsyncMock()):
            await client.on_raw_pong(msg)
        assert client._ready is True

    @pytest.mark.asyncio
    async def test_ignores_non_ready_pong(self):
        client, _, _ = _make_client()
        client._ready = False
        msg = _mock_message(params=["server", "other"])
        with patch.object(type(client).__mro__[1], "on_raw_pong", AsyncMock()):
            await client.on_raw_pong(msg)
        assert client._ready is False


# ---------------------------------------------------------------------------
# on_kick
# ---------------------------------------------------------------------------


class TestOnKick:
    @pytest.mark.asyncio
    async def test_no_rejoin_when_auto_rejoin_disabled(self):
        client, _, _ = _make_client(auto_rejoin=False)
        client.nickname = "bot"
        client.join = AsyncMock()
        with patch.object(type(client).__mro__[1], "on_kick", AsyncMock()):
            await client.on_kick("#test", "bot", "op")
        client.join.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_rejoin_when_different_user_kicked(self):
        client, _, _ = _make_client()
        client.nickname = "bot"
        client.join = AsyncMock()
        with patch.object(type(client).__mro__[1], "on_kick", AsyncMock()):
            await client.on_kick("#test", "otheruser", "op")
        client.join.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_rejoin_on_ban_reason(self):
        client, _, _ = _make_client()
        client.nickname = "bot"
        client.join = AsyncMock()
        with patch.object(type(client).__mro__[1], "on_kick", AsyncMock()):
            await client.on_kick("#test", "bot", "op", reason="ban evasion")
        client.join.assert_not_called()

    @pytest.mark.asyncio
    async def test_rejoins_after_kick(self):
        client, _, _ = _make_client(rejoin_delay=0)
        client.nickname = "bot"
        client.join = AsyncMock()
        with patch.object(type(client).__mro__[1], "on_kick", AsyncMock()):
            await client.on_kick("#test", "bot", "op", reason="spam")
        client.join.assert_awaited_once_with("#test")


# ---------------------------------------------------------------------------
# on_message
# ---------------------------------------------------------------------------


class TestOnMessage:
    @pytest.mark.asyncio
    async def test_skips_when_not_ready(self):
        client, bus, _ = _make_client()
        client._ready = False
        with patch.object(type(client).__mro__[1], "on_message", AsyncMock()):
            await client.on_message("#test", "user", "hello")
        bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_private_message(self):
        client, bus, _ = _make_client()
        with patch.object(type(client).__mro__[1], "on_message", AsyncMock()):
            await client.on_message("bot", "user", "hello")
        bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_no_mapping(self):
        client, bus, router = _make_client()
        router.get_mapping_for_irc.return_value = None
        with patch.object(type(client).__mro__[1], "on_message", AsyncMock()):
            await client.on_message("#test", "user", "hello")
        bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_publishes_message_with_msgid(self):
        client, bus, router = _make_client()
        router.get_mapping_for_irc.return_value = MagicMock(discord_channel_id="111")
        client._message_tags = {"msgid": "irc-abc", "+draft/reply": None}
        with patch.object(type(client).__mro__[1], "on_message", AsyncMock()):
            await client.on_message("#test", "user", "hello")
        bus.publish.assert_called_once()
        _, evt = bus.publish.call_args[0]
        assert evt.message_id == "irc-abc"

    @pytest.mark.asyncio
    async def test_resolves_reply_to_discord_id(self):
        client, bus, router = _make_client()
        router.get_mapping_for_irc.return_value = MagicMock(discord_channel_id="111")
        client._msgid_tracker.store("irc-orig", "discord-orig")
        client._message_tags = {"msgid": "irc-new", "+draft/reply": "irc-orig"}
        with patch.object(type(client).__mro__[1], "on_message", AsyncMock()):
            await client.on_message("#test", "user", "reply msg")
        _, evt = bus.publish.call_args[0]
        assert evt.reply_to_id == "discord-orig"

    @pytest.mark.asyncio
    async def test_echo_correlates_pending_send(self):
        client, _bus, router = _make_client()
        router.get_mapping_for_irc.return_value = MagicMock(discord_channel_id="111")
        client.nickname = "bot"
        client._pending_sends.put_nowait("discord-123")
        client._message_tags = {"msgid": "irc-echo"}
        with patch.object(type(client).__mro__[1], "on_message", AsyncMock()):
            await client.on_message("#test", "bot", "echoed msg")
        assert client._msgid_tracker.get_discord_id("irc-echo") == "discord-123"


# ---------------------------------------------------------------------------
# on_ctcp_action
# ---------------------------------------------------------------------------


class TestOnCtcpAction:
    @pytest.mark.asyncio
    async def test_skips_private_action(self):
        client, bus, _ = _make_client()
        # pydle.Client may not define on_ctcp_action; patch at the mixin level
        with patch("pydle.features.ctcp.CTCPSupport.on_ctcp_action", AsyncMock(), create=True):
            await client.on_ctcp_action("user", "bot", "dances")
        bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_no_mapping(self):
        client, bus, router = _make_client()
        router.get_mapping_for_irc.return_value = None
        with patch("pydle.features.ctcp.CTCPSupport.on_ctcp_action", AsyncMock(), create=True):
            await client.on_ctcp_action("user", "#test", "dances")
        bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_publishes_action_with_asterisk_prefix(self):
        client, bus, router = _make_client()
        router.get_mapping_for_irc.return_value = MagicMock(discord_channel_id="111")
        with patch("pydle.features.ctcp.CTCPSupport.on_ctcp_action", AsyncMock(), create=True):
            await client.on_ctcp_action("user", "#test", "dances")
        _, evt = bus.publish.call_args[0]
        assert evt.content == "* user dances"
        assert evt.is_action is True


# ---------------------------------------------------------------------------
# on_raw_tagmsg
# ---------------------------------------------------------------------------


class TestOnRawTagmsg:
    @pytest.mark.asyncio
    async def test_skips_when_not_ready(self):
        client, bus, _ = _make_client()
        client._ready = False
        await client.on_raw_tagmsg(_mock_message(params=["#test"]))
        bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_no_params(self):
        client, bus, _ = _make_client()
        await client.on_raw_tagmsg(_mock_message(params=[]))
        bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_private_target(self):
        client, bus, _ = _make_client()
        await client.on_raw_tagmsg(_mock_message(params=["bot"]))
        bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_no_mapping(self):
        client, bus, router = _make_client()
        router.get_mapping_for_irc.return_value = None
        await client.on_raw_tagmsg(_mock_message(params=["#test"]))
        bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_publishes_reaction_on_react_tag(self):
        client, bus, router = _make_client()
        router.get_mapping_for_irc.return_value = MagicMock(discord_channel_id="111")
        client._msgid_tracker.store("irc-orig", "discord-orig")
        msg = _mock_message(
            params=["#test"],
            tags={"+draft/reply": "irc-orig", "+draft/react": "👍"},
            source="user!user@host",
        )
        await client.on_raw_tagmsg(msg)
        bus.publish.assert_called_once()
        _, evt = bus.publish.call_args[0]
        assert evt.emoji == "👍"
        assert evt.message_id == "discord-orig"
        assert evt.author_id == "user"

    @pytest.mark.asyncio
    async def test_skips_reaction_when_no_discord_id(self):
        client, bus, router = _make_client()
        router.get_mapping_for_irc.return_value = MagicMock(discord_channel_id="111")
        msg = _mock_message(
            params=["#test"],
            tags={"+draft/reply": "unknown-irc-id", "+draft/react": "👍"},
        )
        await client.on_raw_tagmsg(msg)
        bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_publishes_typing_on_typing_tag(self):
        client, bus, router = _make_client()
        router.get_mapping_for_irc.return_value = MagicMock(discord_channel_id="111")
        msg = _mock_message(params=["#test"], tags={"typing": "active"}, source="user!u@h")
        await client.on_raw_tagmsg(msg)
        bus.publish.assert_called_once()
        _, evt = bus.publish.call_args[0]
        assert evt.user_id == "user"

    @pytest.mark.asyncio
    async def test_publishes_reaction_removal_on_unreact_tag(self):
        """+draft/unreact TAGMSG emits ReactionIn with is_remove=True."""
        client, bus, router = _make_client()
        router.get_mapping_for_irc.return_value = MagicMock(discord_channel_id="111")
        client._msgid_tracker.store("irc-orig", "discord-orig")
        msg = _mock_message(
            params=["#test"],
            tags={"+draft/reply": "irc-orig", "+draft/unreact": "👍"},
            source="user!user@host",
        )
        await client.on_raw_tagmsg(msg)
        bus.publish.assert_called_once()
        _, evt = bus.publish.call_args[0]
        assert evt.emoji == "👍"
        assert evt.message_id == "discord-orig"
        assert evt.author_id == "user"
        assert evt.raw.get("is_remove") is True

    @pytest.mark.asyncio
    async def test_skips_unreact_when_no_discord_id(self):
        client, bus, router = _make_client()
        router.get_mapping_for_irc.return_value = MagicMock(discord_channel_id="111")
        msg = _mock_message(
            params=["#test"],
            tags={"+draft/reply": "unknown-irc-id", "+draft/unreact": "👍"},
            source="user!u@h",
        )
        await client.on_raw_tagmsg(msg)
        bus.publish.assert_not_called()


# ---------------------------------------------------------------------------
# on_raw_redact
# ---------------------------------------------------------------------------


class TestOnRawRedact:
    @pytest.mark.asyncio
    async def test_skips_too_few_params(self):
        client, bus, _ = _make_client()
        await client.on_raw_redact(_mock_message(params=["#test"]))
        bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_private_target(self):
        client, bus, _ = _make_client()
        await client.on_raw_redact(_mock_message(params=["bot", "irc-id"]))
        bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_no_mapping(self):
        client, bus, router = _make_client()
        router.get_mapping_for_irc.return_value = None
        await client.on_raw_redact(_mock_message(params=["#test", "irc-id"]))
        bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_no_discord_id(self):
        client, bus, router = _make_client()
        router.get_mapping_for_irc.return_value = MagicMock(discord_channel_id="111")
        await client.on_raw_redact(_mock_message(params=["#test", "unknown-irc-id"]))
        bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_publishes_message_delete(self):
        client, bus, router = _make_client()
        router.get_mapping_for_irc.return_value = MagicMock(discord_channel_id="111")
        client._msgid_tracker.store("irc-id", "discord-id")
        await client.on_raw_redact(_mock_message(params=["#test", "irc-id"]))
        bus.publish.assert_called_once()
        _, evt = bus.publish.call_args[0]
        assert evt.message_id == "discord-id"


# ---------------------------------------------------------------------------
# _send_message
# ---------------------------------------------------------------------------


class TestSendMessage:
    @pytest.mark.asyncio
    async def test_skips_no_mapping(self):
        client, _, router = _make_client()
        router.get_mapping_for_discord.return_value = None
        client.message = AsyncMock()
        evt = MagicMock()
        evt.channel_id = "111"
        await client._send_message(evt)
        client.message.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_with_reply_tag(self):
        client, _, router = _make_client()
        irc_target = MagicMock()
        irc_target.channel = "#test"
        router.get_mapping_for_discord.return_value = MagicMock(irc=irc_target)
        client._msgid_tracker.store("irc-orig", "discord-orig")
        client.rawmsg = AsyncMock()
        client.message = AsyncMock()

        evt = MagicMock()
        evt.channel_id = "111"
        evt.content = "reply text"
        evt.message_id = "discord-new"
        evt.reply_to_id = "discord-orig"

        await client._send_message(evt)
        client.rawmsg.assert_awaited_once()
        args = client.rawmsg.call_args
        assert args[1]["tags"]["+draft/reply"] == "irc-orig"

    @pytest.mark.asyncio
    async def test_sends_without_reply_tag(self):
        client, _, router = _make_client()
        irc_target = MagicMock()
        irc_target.channel = "#test"
        router.get_mapping_for_discord.return_value = MagicMock(irc=irc_target)
        client.message = AsyncMock()

        evt = MagicMock()
        evt.channel_id = "111"
        evt.content = "hello"
        evt.message_id = "discord-1"
        evt.reply_to_id = None

        await client._send_message(evt)
        client.message.assert_awaited_once_with("#test", "hello")

    @pytest.mark.asyncio
    async def test_queues_pending_send_for_echo(self):
        client, _, router = _make_client()
        irc_target = MagicMock()
        irc_target.channel = "#test"
        router.get_mapping_for_discord.return_value = MagicMock(irc=irc_target)
        client.message = AsyncMock()

        evt = MagicMock()
        evt.channel_id = "111"
        evt.content = "hello"
        evt.message_id = "discord-1"
        evt.reply_to_id = None

        await client._send_message(evt)
        assert client._pending_sends.get_nowait() == "discord-1"

    @pytest.mark.asyncio
    async def test_sends_relaymsg_when_capability_negotiated(self):
        """When draft/relaymsg is negotiated, use RELAYMSG instead of PRIVMSG."""
        client, _, router = _make_client()
        client._capabilities = {"draft/relaymsg": True}
        irc_target = MagicMock()
        irc_target.channel = "#test"
        router.get_mapping_for_discord.return_value = MagicMock(irc=irc_target)
        client.rawmsg = AsyncMock()

        evt = MagicMock()
        evt.channel_id = "111"
        evt.content = "hello"
        evt.message_id = "discord-1"
        evt.reply_to_id = None
        evt.author_display = "Alice"
        evt.author_id = "123"

        await client._send_message(evt)
        client.rawmsg.assert_awaited_once_with("RELAYMSG", "#test", "Alice/d", "hello")

    @pytest.mark.asyncio
    async def test_sends_relaymsg_clean_nick_when_configured(self):
        """When irc_relaymsg_clean_nicks is true, no /d suffix on spoofed nick."""
        with patch("bridge.adapters.irc.client.cfg") as mock_cfg:
            mock_cfg.irc_relaymsg_clean_nicks = True
            client, _, router = _make_client()
            client._capabilities = {"draft/relaymsg": True}
            irc_target = MagicMock()
            irc_target.channel = "#test"
            router.get_mapping_for_discord.return_value = MagicMock(irc=irc_target)
            client.rawmsg = AsyncMock()

            evt = MagicMock()
            evt.channel_id = "111"
            evt.content = "hello"
            evt.message_id = "discord-1"
            evt.reply_to_id = None
            evt.author_display = "Alice"
            evt.author_id = "123"

            await client._send_message(evt)
            client.rawmsg.assert_awaited_once_with("RELAYMSG", "#test", "Alice", "hello")


# ---------------------------------------------------------------------------
# queue_message
# ---------------------------------------------------------------------------


def test_queue_message():
    client, _, _ = _make_client()
    evt = MagicMock()
    client.queue_message(evt)
    assert client._outbound.qsize() == 1


# ---------------------------------------------------------------------------
# Edge cases / race conditions
# ---------------------------------------------------------------------------


class TestIRCClientEdgeCases:
    # --- on_kick: case-insensitive nick comparison ---

    @pytest.mark.asyncio
    async def test_kick_case_insensitive_nick_match(self):
        client, _, _ = _make_client(rejoin_delay=0)
        client.nickname = "Bot"  # mixed case
        client.join = AsyncMock()
        with patch.object(type(client).__mro__[1], "on_kick", AsyncMock()):
            await client.on_kick("#test", "BOT", "op")  # uppercase
        client.join.assert_awaited_once_with("#test")

    # --- on_raw_tagmsg: react tag without reply tag (no reaction published) ---

    @pytest.mark.asyncio
    async def test_tagmsg_react_without_reply_tag_skips(self):
        client, bus, router = _make_client()
        router.get_mapping_for_irc.return_value = MagicMock(discord_channel_id="111")
        msg = _mock_message(
            params=["#test"],
            tags={"+draft/react": "👍"},  # no +draft/reply
            source="user!u@h",
        )
        await client.on_raw_tagmsg(msg)
        bus.publish.assert_not_called()

    # --- on_message: empty content still publishes ---

    @pytest.mark.asyncio
    async def test_message_empty_content_still_publishes(self):
        client, bus, router = _make_client()
        router.get_mapping_for_irc.return_value = MagicMock(discord_channel_id="111")
        client._message_tags = {}
        with patch.object(type(client).__mro__[1], "on_message", AsyncMock()):
            await client.on_message("#test", "user", "")
        bus.publish.assert_called_once()
        _, evt = bus.publish.call_args[0]
        assert evt.content == ""

    # --- _send_message: reply_to_id set but no irc_msgid found ---

    @pytest.mark.asyncio
    async def test_send_message_reply_to_id_not_found_sends_without_tag(self):
        client, _, router = _make_client()
        irc_target = MagicMock()
        irc_target.channel = "#test"
        router.get_mapping_for_discord.return_value = MagicMock(irc=irc_target)
        client.message = AsyncMock()

        evt = MagicMock()
        evt.channel_id = "111"
        evt.content = "reply"
        evt.message_id = "discord-new"
        evt.reply_to_id = "discord-orig"  # not in tracker

        await client._send_message(evt)
        # Falls back to plain message (no rawmsg with tags)
        client.message.assert_awaited_once_with("#test", "reply")

    # --- on_message: no _message_tags attribute (older pydle) ---

    @pytest.mark.asyncio
    async def test_message_without_message_tags_attr_uses_fallback_id(self):
        client, bus, router = _make_client()
        router.get_mapping_for_irc.return_value = MagicMock(discord_channel_id="111")
        # Ensure _message_tags is not set
        if hasattr(client, "_message_tags"):
            del client._message_tags
        with patch.object(type(client).__mro__[1], "on_message", AsyncMock()):
            await client.on_message("#test", "user", "hello")
        _, evt = bus.publish.call_args[0]
        assert evt.message_id.startswith("irc:")


# ---------------------------------------------------------------------------
# _connect_with_backoff
# ---------------------------------------------------------------------------


class TestConnectWithBackoff:
    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        from bridge.adapters.irc import _connect_with_backoff

        mock_client = AsyncMock()
        mock_client.connected = False  # pydle returns immediately; we wait for disconnect
        call_count = 0

        async def fake_connect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise asyncio.CancelledError()

        mock_client.connect.side_effect = fake_connect
        with pytest.raises(asyncio.CancelledError), patch("asyncio.sleep", AsyncMock()):
            await _connect_with_backoff(mock_client, "irc.example.com", 6697, True)
        assert call_count >= 1

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self):
        from bridge.adapters.irc import _connect_with_backoff

        mock_client = AsyncMock()
        mock_client.connected = False  # simulate disconnect so we don't wait forever
        call_count = 0

        async def fake_connect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionRefusedError("refused")
            raise asyncio.CancelledError()

        mock_client.connect.side_effect = fake_connect
        with pytest.raises(asyncio.CancelledError), patch("asyncio.sleep", AsyncMock()):
            await _connect_with_backoff(mock_client, "irc.example.com", 6697, True)
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_attempts(self):
        from bridge.adapters.irc import _MAX_ATTEMPTS, _connect_with_backoff

        mock_client = AsyncMock()
        mock_client.connect.side_effect = ConnectionRefusedError("refused")
        with pytest.raises(ConnectionRefusedError), patch("asyncio.sleep", AsyncMock()):
            await _connect_with_backoff(mock_client, "irc.example.com", 6697, True)
        assert mock_client.connect.call_count == _MAX_ATTEMPTS


# ---------------------------------------------------------------------------
# Echo-message correlation (lines 195–196)
# ---------------------------------------------------------------------------


class TestEchoMessageCorrelation:
    @pytest.mark.asyncio
    async def test_echo_from_self_stores_msgid_mapping(self):
        client, _bus, router = _make_client(nick="bot")
        client.nickname = "bot"  # pydle sets this on connect; set manually for tests
        router.get_mapping_for_irc.return_value = MagicMock(discord_channel_id="111")
        client._pending_sends.put_nowait("discord-msg-1")
        client._message_tags = {"msgid": "irc-abc"}
        with patch.object(type(client).__mro__[1], "on_message", AsyncMock()):
            await client.on_message("#test", "bot", "hello")
        assert client._msgid_tracker.get_discord_id("irc-abc") == "discord-msg-1"

    @pytest.mark.asyncio
    async def test_echo_with_empty_pending_queue_does_not_crash(self):
        client, _bus, router = _make_client(nick="bot")
        client.nickname = "bot"
        router.get_mapping_for_irc.return_value = MagicMock(discord_channel_id="111")
        client._message_tags = {"msgid": "irc-xyz"}
        with patch.object(type(client).__mro__[1], "on_message", AsyncMock()):
            await client.on_message("#test", "bot", "hello")
        assert client._msgid_tracker.get_discord_id("irc-xyz") is None


# ---------------------------------------------------------------------------
# Typing throttle (line 368–372)
# ---------------------------------------------------------------------------


class TestTypingThrottle:
    @pytest.mark.asyncio
    async def test_typing_suppressed_within_3s(self):
        from bridge.adapters.irc import IRCAdapter
        from bridge.events import TypingOut

        bus = MagicMock()
        router = MagicMock()
        adapter = IRCAdapter(bus, router, identity_resolver=None)
        mock_client = MagicMock()
        mock_client.rawmsg = AsyncMock()
        mock_client._typing_last = 9999999999.0  # far future → within 3s
        adapter._client = mock_client

        irc_target = MagicMock()
        irc_target.channel = "#test"
        router.get_mapping_for_discord.return_value = MagicMock(irc=irc_target)

        evt = TypingOut(target_origin="irc", channel_id="111")
        await adapter._send_typing(evt)
        mock_client.rawmsg.assert_not_called()

    @pytest.mark.asyncio
    async def test_typing_sent_after_3s_elapsed(self):
        from bridge.adapters.irc import IRCAdapter
        from bridge.events import TypingOut

        bus = MagicMock()
        router = MagicMock()
        adapter = IRCAdapter(bus, router, identity_resolver=None)
        mock_client = MagicMock()
        mock_client.rawmsg = AsyncMock()
        mock_client._typing_last = 0.0  # long ago
        adapter._client = mock_client

        irc_target = MagicMock()
        irc_target.channel = "#test"
        router.get_mapping_for_discord.return_value = MagicMock(irc=irc_target)

        evt = TypingOut(target_origin="irc", channel_id="111")
        await adapter._send_typing(evt)
        mock_client.rawmsg.assert_awaited_once()


# ---------------------------------------------------------------------------
# Puppet send path (lines 474–475)
# ---------------------------------------------------------------------------


class TestPuppetSendPath:
    @pytest.mark.asyncio
    async def test_send_via_puppet_uses_puppet_when_has_irc(self):
        from unittest.mock import AsyncMock

        from bridge.adapters.irc import IRCAdapter

        bus = MagicMock()
        router = MagicMock()
        identity = MagicMock()
        identity.has_irc = AsyncMock(return_value=True)
        adapter = IRCAdapter(bus, router, identity_resolver=identity)
        adapter._puppet_manager = MagicMock()
        adapter._puppet_manager.send_message = AsyncMock()

        irc_target = MagicMock()
        irc_target.channel = "#test"
        router.get_mapping_for_discord.return_value = MagicMock(irc=irc_target)

        evt = MagicMock()
        evt.channel_id = "111"
        evt.author_id = "u1"
        evt.content = "hi"
        evt.avatar_url = None
        await adapter._send_via_puppet(evt)
        adapter._puppet_manager.send_message.assert_awaited_once_with("u1", "#test", "hi", avatar_url=None)

    @pytest.mark.asyncio
    async def test_send_via_puppet_falls_back_to_client_when_no_irc(self):
        from unittest.mock import AsyncMock

        from bridge.adapters.irc import IRCAdapter

        bus = MagicMock()
        router = MagicMock()
        identity = MagicMock()
        identity.has_irc = AsyncMock(return_value=False)
        adapter = IRCAdapter(bus, router, identity_resolver=identity)
        adapter._puppet_manager = MagicMock()
        mock_client = MagicMock()
        mock_client.queue_message = MagicMock()
        adapter._client = mock_client

        irc_target = MagicMock()
        irc_target.channel = "#test"
        router.get_mapping_for_discord.return_value = MagicMock(irc=irc_target)

        evt = MagicMock()
        evt.channel_id = "111"
        evt.author_id = "u1"
        evt.content = "hi"
        await adapter._send_via_puppet(evt)
        mock_client.queue_message.assert_called_once_with(evt)
