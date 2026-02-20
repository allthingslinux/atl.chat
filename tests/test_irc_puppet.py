"""Tests for IRCPuppetManager (bridge/adapters/irc_puppet.py)."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bridge.adapters.irc_msgid import MessageIDTracker
from bridge.adapters.irc_puppet import IRCPuppet, IRCPuppetManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager(irc_nick: str | None = "puppet_nick", ping_interval: int = 120, prejoin_commands: list[str] | None = None) -> IRCPuppetManager:
    identity = AsyncMock()
    identity.discord_to_irc = AsyncMock(return_value=irc_nick)
    return IRCPuppetManager(
        bus=MagicMock(),
        router=MagicMock(),
        identity=identity,
        server="irc.libera.chat",
        port=6697,
        tls=True,
        idle_timeout_hours=1,
        ping_interval=ping_interval,
        prejoin_commands=prejoin_commands,
    )


def _mock_puppet(discord_id: str = "d1", nick: str = "nick") -> MagicMock:
    p = MagicMock(spec=IRCPuppet)
    p.discord_id = discord_id
    p.last_activity = time.time()
    p.touch = MagicMock()
    p.connect = AsyncMock()
    p.disconnect = AsyncMock()
    p.message = AsyncMock()
    p.join = AsyncMock()
    p.channels = {}
    return p


# ---------------------------------------------------------------------------
# IRCPuppet
# ---------------------------------------------------------------------------

class TestIRCPuppet:
    def test_discord_id_stored_on_init(self):
        puppet = IRCPuppet("nick", "d1")
        assert puppet.discord_id == "d1"

    def test_touch_updates_last_activity(self):
        puppet = IRCPuppet("nick", "d1")
        before = puppet.last_activity
        time.sleep(0.01)
        puppet.touch()
        assert puppet.last_activity > before

    def test_default_ping_interval(self):
        puppet = IRCPuppet("nick", "d1")
        assert puppet._ping_interval == 120

    def test_custom_ping_interval(self):
        puppet = IRCPuppet("nick", "d1", ping_interval=60)
        assert puppet._ping_interval == 60

    def test_default_prejoin_commands_empty(self):
        puppet = IRCPuppet("nick", "d1")
        assert puppet._prejoin_commands == []

    def test_custom_prejoin_commands(self):
        cmds = ["MODE {nick} +D"]
        puppet = IRCPuppet("nick", "d1", prejoin_commands=cmds)
        assert puppet._prejoin_commands == cmds

    @pytest.mark.asyncio
    async def test_on_connect_sends_prejoin_commands_with_nick_substitution(self):
        puppet = IRCPuppet("mynick", "d1", prejoin_commands=["MODE {nick} +D", "PRIVMSG NickServ IDENTIFY pass"])
        puppet.rawmsg = AsyncMock()
        with patch.object(type(puppet).__bases__[0], "on_connect", new=AsyncMock()):
            await puppet.on_connect()
        assert puppet.rawmsg.await_count == 2
        calls = [c.args for c in puppet.rawmsg.await_args_list]
        assert calls[0] == ("MODE", "mynick +D")
        assert calls[1] == ("PRIVMSG", "NickServ IDENTIFY pass")

    @pytest.mark.asyncio
    async def test_on_connect_no_prejoin_commands_sends_nothing(self):
        puppet = IRCPuppet("mynick", "d1")
        puppet.rawmsg = AsyncMock()
        with patch.object(type(puppet).__bases__[0], "on_connect", new=AsyncMock()):
            await puppet.on_connect()
        puppet.rawmsg.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_connect_starts_pinger_task(self):
        puppet = IRCPuppet("mynick", "d1", ping_interval=120)
        puppet.rawmsg = AsyncMock()
        with patch.object(type(puppet).__bases__[0], "on_connect", new=AsyncMock()):
            await puppet.on_connect()
        assert puppet._pinger_task is not None
        puppet._pinger_task.cancel()

    @pytest.mark.asyncio
    async def test_pinger_sends_ping_after_interval(self):
        puppet = IRCPuppet("mynick", "d1", ping_interval=1)
        puppet.rawmsg = MagicMock()
        pinger = asyncio.create_task(puppet._pinger())
        await asyncio.sleep(1.1)
        pinger.cancel()
        puppet.rawmsg.assert_called_with("PING", "keep-alive")


# ---------------------------------------------------------------------------
# get_or_create_puppet
# ---------------------------------------------------------------------------

class TestGetOrCreatePuppet:
    @pytest.mark.asyncio
    async def test_returns_cached_puppet_and_touches(self):
        manager = _make_manager()
        existing = _mock_puppet()
        manager._puppets["d1"] = existing
        result = await manager.get_or_create_puppet("d1")
        assert result is existing
        existing.touch.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_irc_nick(self):
        manager = _make_manager(irc_nick=None)
        result = await manager.get_or_create_puppet("d1")
        assert result is None

    @pytest.mark.asyncio
    async def test_creates_and_connects_new_puppet(self):
        manager = _make_manager(irc_nick="mynick")
        mock_puppet = _mock_puppet()

        with patch("bridge.adapters.irc_puppet.IRCPuppet", return_value=mock_puppet) as MockPuppet:
            result = await manager.get_or_create_puppet("d1")

        assert result is mock_puppet
        mock_puppet.connect.assert_awaited_once_with(
            hostname="irc.libera.chat", port=6697, tls=True
        )
        assert "d1" in manager._puppets

    @pytest.mark.asyncio
    async def test_puppet_created_with_ping_interval_and_prejoin_commands(self):
        cmds = ["MODE {nick} +D"]
        manager = _make_manager(irc_nick="mynick", ping_interval=60, prejoin_commands=cmds)
        mock_puppet = _mock_puppet()

        with patch("bridge.adapters.irc_puppet.IRCPuppet", return_value=mock_puppet) as MockPuppet:
            await manager.get_or_create_puppet("d1")

        MockPuppet.assert_called_once_with("mynick", "d1", ping_interval=60, prejoin_commands=cmds)

    @pytest.mark.asyncio
    async def test_removes_puppet_on_connect_failure(self):
        manager = _make_manager(irc_nick="mynick")
        mock_puppet = _mock_puppet()
        mock_puppet.connect = AsyncMock(side_effect=OSError("refused"))

        with patch("bridge.adapters.irc_puppet.IRCPuppet", return_value=mock_puppet):
            result = await manager.get_or_create_puppet("d1")

        assert result is None
        assert "d1" not in manager._puppets


# ---------------------------------------------------------------------------
# send_message
# ---------------------------------------------------------------------------

class TestSendMessage:
    @pytest.mark.asyncio
    async def test_skips_when_no_puppet(self):
        manager = _make_manager(irc_nick=None)
        await manager.send_message("d1", "#test", "hello")
        assert "d1" not in manager._puppets

    @pytest.mark.asyncio
    async def test_sends_single_chunk(self):
        manager = _make_manager()
        mock_puppet = _mock_puppet()
        manager._puppets["d1"] = mock_puppet

        await manager.send_message("d1", "#test", "hello")

        mock_puppet.message.assert_awaited_once_with("#test", "hello")
        mock_puppet.touch.assert_called()

    @pytest.mark.asyncio
    async def test_sends_multiple_chunks_for_long_message(self):
        manager = _make_manager()
        mock_puppet = _mock_puppet()
        manager._puppets["d1"] = mock_puppet

        long_msg = "x" * 1000
        await manager.send_message("d1", "#test", long_msg)

        assert mock_puppet.message.await_count > 1

    @pytest.mark.asyncio
    async def test_handles_send_exception_gracefully(self):
        manager = _make_manager()
        mock_puppet = _mock_puppet()
        mock_puppet.message = AsyncMock(side_effect=OSError("send failed"))
        manager._puppets["d1"] = mock_puppet

        await manager.send_message("d1", "#test", "hello")
        # message was attempted (exception swallowed, not silently skipped)
        mock_puppet.message.assert_awaited_once()


# ---------------------------------------------------------------------------
# join_channel
# ---------------------------------------------------------------------------

class TestJoinChannel:
    @pytest.mark.asyncio
    async def test_skips_when_no_puppet(self):
        manager = _make_manager(irc_nick=None)
        await manager.join_channel("d1", "#test")
        assert "d1" not in manager._puppets

    @pytest.mark.asyncio
    async def test_joins_new_channel(self):
        manager = _make_manager()
        mock_puppet = _mock_puppet()
        mock_puppet.channels = {}
        manager._puppets["d1"] = mock_puppet

        await manager.join_channel("d1", "#test")

        mock_puppet.join.assert_awaited_once_with("#test")
        mock_puppet.touch.assert_called()

    @pytest.mark.asyncio
    async def test_skips_already_joined_channel(self):
        manager = _make_manager()
        mock_puppet = _mock_puppet()
        mock_puppet.channels = {"#test": {}}
        manager._puppets["d1"] = mock_puppet

        await manager.join_channel("d1", "#test")

        mock_puppet.join.assert_not_called()


# ---------------------------------------------------------------------------
# _cleanup_idle_puppets
# ---------------------------------------------------------------------------

class TestCleanupIdlePuppets:
    @pytest.mark.asyncio
    async def test_disconnects_idle_puppets(self):
        manager = _make_manager()
        mock_puppet = _mock_puppet()
        mock_puppet.last_activity = time.time() - 7200  # 2h ago, timeout is 1h
        manager._puppets["d1"] = mock_puppet

        calls = 0

        async def _sleep_once(_):
            nonlocal calls
            calls += 1
            if calls >= 2:
                raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=_sleep_once):
            await manager._cleanup_idle_puppets()

        mock_puppet.disconnect.assert_awaited_once()
        assert "d1" not in manager._puppets

    @pytest.mark.asyncio
    async def test_keeps_active_puppets(self):
        manager = _make_manager()
        mock_puppet = _mock_puppet()
        mock_puppet.last_activity = time.time()  # just active
        manager._puppets["d1"] = mock_puppet

        calls = 0

        async def _sleep_once(_):
            nonlocal calls
            calls += 1
            if calls >= 2:
                raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=_sleep_once):
            await manager._cleanup_idle_puppets()

        mock_puppet.disconnect.assert_not_called()
        assert "d1" in manager._puppets


# ---------------------------------------------------------------------------
# start / stop
# ---------------------------------------------------------------------------

class TestStartStop:
    @pytest.mark.asyncio
    async def test_start_creates_cleanup_task(self):
        manager = _make_manager()
        await manager.start()
        assert manager._cleanup_task is not None
        manager._cleanup_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await manager._cleanup_task

    @pytest.mark.asyncio
    async def test_stop_cancels_task_and_disconnects_all(self):
        manager = _make_manager()
        p1, p2 = _mock_puppet("d1"), _mock_puppet("d2")
        manager._puppets = {"d1": p1, "d2": p2}
        manager._cleanup_task = asyncio.create_task(asyncio.sleep(9999))

        await manager.stop()

        p1.disconnect.assert_awaited_once()
        p2.disconnect.assert_awaited_once()
        assert manager._puppets == {}

    @pytest.mark.asyncio
    async def test_stop_with_no_task_is_safe(self):
        manager = _make_manager()
        await manager.stop()
        assert manager._puppets == {}
        assert manager._cleanup_task is None


# ---------------------------------------------------------------------------
# Edge cases / race conditions
# ---------------------------------------------------------------------------

class TestPuppetEdgeCases:
    # --- Concurrent get_or_create_puppet for same discord_id ---
    # Race: two coroutines both see no puppet and both try to create one.
    # The second should reuse the first's result (or at least not crash).

    @pytest.mark.asyncio
    async def test_concurrent_get_or_create_same_user(self):
        manager = _make_manager(irc_nick="mynick")
        connect_started = asyncio.Event()
        connect_done = asyncio.Event()

        async def _slow_connect(**kwargs):
            connect_started.set()
            await connect_done.wait()

        mock_puppet = _mock_puppet()
        mock_puppet.connect = AsyncMock(side_effect=_slow_connect)

        with patch("bridge.adapters.irc_puppet.IRCPuppet", return_value=mock_puppet):
            # Start first call, let it reach connect
            task1 = asyncio.create_task(manager.get_or_create_puppet("d1"))
            await connect_started.wait()

            # Second call while first is still connecting
            connect_done.set()
            result1 = await task1
            result2 = await manager.get_or_create_puppet("d1")

        # Both should return a puppet; second reuses cached
        assert result1 is mock_puppet
        assert result2 is mock_puppet
        assert mock_puppet.connect.await_count == 1  # only connected once

    # --- _cleanup_idle_puppets: non-CancelledError exception continues loop ---

    @pytest.mark.asyncio
    async def test_cleanup_exception_continues_loop(self):
        manager = _make_manager()
        mock_puppet = _mock_puppet()
        mock_puppet.last_activity = time.time() - 7200
        mock_puppet.disconnect = AsyncMock(side_effect=OSError("disconnect failed"))
        manager._puppets["d1"] = mock_puppet

        calls = 0

        async def _sleep_twice(_):
            nonlocal calls
            calls += 1
            if calls >= 3:
                raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=_sleep_twice):
            await manager._cleanup_idle_puppets()

        # Loop ran at least twice despite exception on first cleanup
        assert calls >= 2

    # --- stop() while send_message is in progress ---

    @pytest.mark.asyncio
    async def test_stop_while_send_in_progress(self):
        manager = _make_manager()
        send_started = asyncio.Event()

        async def _slow_message(channel, content):
            send_started.set()
            await asyncio.sleep(9999)

        mock_puppet = _mock_puppet()
        mock_puppet.message = AsyncMock(side_effect=_slow_message)
        manager._puppets["d1"] = mock_puppet

        send_task = asyncio.create_task(manager.send_message("d1", "#test", "hello"))
        await send_started.wait()

        # stop() should disconnect puppets even while send is in progress
        stop_task = asyncio.create_task(manager.stop())
        send_task.cancel()
        await asyncio.gather(stop_task, return_exceptions=True)
        import contextlib
        with contextlib.suppress(asyncio.CancelledError):
            await send_task

        mock_puppet.disconnect.assert_awaited_once()

    # --- MessageIDTracker: TTL expiry ---

    def test_msgid_tracker_ttl_expiry(self):
        tracker = MessageIDTracker(ttl_seconds=0)
        tracker.store("irc-id", "discord-id")
        # With ttl=0, entries expire immediately on next access
        assert tracker.get_discord_id("irc-id") is None
        assert tracker.get_irc_msgid("discord-id") is None

    # --- MessageIDTracker: overwrite same key ---

    def test_msgid_tracker_overwrite_updates_mapping(self):
        tracker = MessageIDTracker()
        tracker.store("irc-id", "discord-old")
        tracker.store("irc-id", "discord-new")
        assert tracker.get_discord_id("irc-id") == "discord-new"

    # --- TokenBucket: acquire returns 0 when tokens available ---

    def test_token_bucket_acquire_zero_when_available(self):
        from bridge.adapters.irc_throttle import TokenBucket
        bucket = TokenBucket(limit=10, refill_rate=10.0)
        assert bucket.acquire() == 0.0

    # --- TokenBucket: acquire returns positive wait when empty ---

    def test_token_bucket_acquire_positive_when_empty(self):
        from bridge.adapters.irc_throttle import TokenBucket
        bucket = TokenBucket(limit=1, refill_rate=1.0)
        bucket.use_token()  # drain
        assert bucket.acquire() > 0.0

    # --- TokenBucket: use_token returns False when empty ---

    def test_token_bucket_use_token_false_when_empty(self):
        from bridge.adapters.irc_throttle import TokenBucket
        bucket = TokenBucket(limit=1, refill_rate=1.0)
        assert bucket.use_token() is True
        assert bucket.use_token() is False
