"""Tests for IRCPuppetManager (bridge/adapters/irc_puppet.py)."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bridge.adapters.irc import IRCPuppet, IRCPuppetManager, MessageIDTracker
from hypothesis import given
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manager(
    irc_nick: str | None = "puppet_nick",
    ping_interval: int = 120,
    prejoin_commands: list[str] | None = None,
) -> IRCPuppetManager:
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
    p.nickname = nick
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

        with patch("bridge.adapters.irc.puppet.IRCPuppet", return_value=mock_puppet):
            result = await manager.get_or_create_puppet("d1")

        assert result is mock_puppet
        mock_puppet.connect.assert_awaited_once_with(hostname="irc.libera.chat", port=6697, tls=True, tls_verify=True)
        assert "d1" in manager._puppets

    @pytest.mark.asyncio
    async def test_puppet_created_with_ping_interval_and_prejoin_commands(self):
        cmds = ["MODE {nick} +D"]
        manager = _make_manager(irc_nick="mynick", ping_interval=60, prejoin_commands=cmds)
        mock_puppet = _mock_puppet()

        with patch("bridge.adapters.irc.puppet.IRCPuppet", return_value=mock_puppet) as mock_cls:
            await manager.get_or_create_puppet("d1")

        mock_cls.assert_called_once_with("mynick", "d1", ping_interval=60, prejoin_commands=cmds)

    @pytest.mark.asyncio
    async def test_removes_puppet_on_connect_failure(self):
        manager = _make_manager(irc_nick="mynick")
        mock_puppet = _mock_puppet()
        mock_puppet.connect = AsyncMock(side_effect=OSError("refused"))

        with patch("bridge.adapters.irc.puppet.IRCPuppet", return_value=mock_puppet):
            result = await manager.get_or_create_puppet("d1")

        assert result is None
        assert "d1" not in manager._puppets


class TestConnectPuppetWithBackoff:
    """Tests for _connect_puppet_with_backoff retry logic."""

    @pytest.mark.asyncio
    async def test_succeeds_after_n_failures(self):
        """Fail N times then succeed — verify correct number of attempts."""
        manager = _make_manager()
        puppet = _mock_puppet()
        # Fail twice, then succeed on third attempt
        puppet.connect = AsyncMock(side_effect=[OSError("fail1"), OSError("fail2"), None])

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await manager._connect_puppet_with_backoff(puppet, max_attempts=5)

        assert result is True
        assert puppet.connect.await_count == 3
        # Two sleeps between the two failures and the success
        assert mock_sleep.await_count == 2

    @pytest.mark.asyncio
    async def test_all_attempts_fail_returns_false(self):
        """All attempts fail — verify max_attempts respected and returns False."""
        manager = _make_manager()
        puppet = _mock_puppet()
        puppet.connect = AsyncMock(side_effect=OSError("refused"))

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await manager._connect_puppet_with_backoff(puppet, max_attempts=4)

        assert result is False
        assert puppet.connect.await_count == 4

    @pytest.mark.asyncio
    async def test_puppet_not_stored_on_failure(self):
        """Puppet is not stored in _puppets when all connect attempts fail."""
        manager = _make_manager(irc_nick="failnick")
        mock_p = _mock_puppet()
        mock_p.connect = AsyncMock(side_effect=OSError("refused"))

        with (
            patch("bridge.adapters.irc.puppet.IRCPuppet", return_value=mock_p),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await manager.get_or_create_puppet("d_fail")

        assert result is None
        assert "d_fail" not in manager._puppets

    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt_no_sleep(self):
        """Immediate success — no sleep calls, returns True."""
        manager = _make_manager()
        puppet = _mock_puppet()
        puppet.connect = AsyncMock()  # succeeds immediately

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await manager._connect_puppet_with_backoff(puppet)

        assert result is True
        assert puppet.connect.await_count == 1
        mock_sleep.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_single_max_attempt_no_retry(self):
        """With max_attempts=1, a single failure returns False with no sleep."""
        manager = _make_manager()
        puppet = _mock_puppet()
        puppet.connect = AsyncMock(side_effect=OSError("fail"))

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await manager._connect_puppet_with_backoff(puppet, max_attempts=1)

        assert result is False
        assert puppet.connect.await_count == 1
        mock_sleep.assert_not_awaited()


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

    @pytest.mark.asyncio
    async def test_send_message_with_avatar_url_sets_metadata_when_cap_available(self):
        """When avatar_url provided and puppet has draft/metadata, sets METADATA avatar."""
        manager = _make_manager()
        mock_puppet = _mock_puppet()
        mock_puppet._capabilities = {"draft/metadata": True}
        mock_puppet._last_avatar_hash = None
        mock_puppet.set_metadata = AsyncMock()
        manager._puppets["d1"] = mock_puppet

        await manager.send_message(
            "d1",
            "#test",
            "hello",
            avatar_url="https://cdn.discord.com/avatars/123/abc.png",
        )

        mock_puppet.set_metadata.assert_awaited_once_with("*", "avatar", "https://cdn.discord.com/avatars/123/abc.png")
        mock_puppet.message.assert_awaited()

    @pytest.mark.asyncio
    async def test_send_message_with_avatar_url_skips_metadata_when_hash_unchanged(self):
        """When avatar_url unchanged, skips METADATA SET (cached by hash)."""
        import hashlib

        manager = _make_manager()
        mock_puppet = _mock_puppet()
        url = "https://cdn.discord.com/avatars/123/abc.png"
        mock_puppet._capabilities = {"draft/metadata": True}
        mock_puppet._last_avatar_hash = hashlib.sha1(url.encode()).hexdigest()
        mock_puppet.set_metadata = AsyncMock()
        manager._puppets["d1"] = mock_puppet

        await manager.send_message("d1", "#test", "hello", avatar_url=url)

        mock_puppet.set_metadata.assert_not_awaited()
        mock_puppet.message.assert_awaited()


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

        with patch("bridge.adapters.irc.puppet.IRCPuppet", return_value=mock_puppet):
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
        from bridge.adapters.irc import TokenBucket

        bucket = TokenBucket(limit=10, refill_rate=10.0)
        assert bucket.acquire() == 0.0

    # --- TokenBucket: acquire returns positive wait when empty ---

    def test_token_bucket_acquire_positive_when_empty(self):
        from bridge.adapters.irc import TokenBucket

        bucket = TokenBucket(limit=1, refill_rate=1.0)
        bucket.use_token()  # drain
        assert bucket.acquire() > 0.0

    # --- TokenBucket: use_token returns False when empty ---

    def test_token_bucket_use_token_false_when_empty(self):
        from bridge.adapters.irc import TokenBucket

        bucket = TokenBucket(limit=1, refill_rate=1.0)
        assert bucket.use_token() is True
        assert bucket.use_token() is False


# ---------------------------------------------------------------------------
# Property-based tests (hypothesis)
# ---------------------------------------------------------------------------


class TestPuppetRetryConvergenceProperty:
    """**Validates: Requirements 4.1, 4.4**

    Property 5: Puppet retry convergence
    For any max_attempts in [1, 10] and any attempt k at which connection
    succeeds, exactly k attempts are made and True is returned; if all fail,
    exactly max_attempts attempts and False.
    """

    @pytest.mark.asyncio
    @given(
        max_attempts=st.integers(min_value=1, max_value=10),
        data=st.data(),
    )
    async def test_puppet_retry_convergence(self, max_attempts: int, data):
        """**Validates: Requirements 4.1, 4.4**"""
        # Draw success_at: either an attempt in [1, max_attempts] or None (all fail)
        success_at = data.draw(
            st.one_of(
                st.integers(min_value=1, max_value=max_attempts),
                st.none(),
            ),
            label="success_at",
        )

        manager = _make_manager()
        puppet = _mock_puppet()

        # Build side effects: fail (k-1) times then succeed at attempt k,
        # or always fail if success_at is None.
        if success_at is not None:
            effects: list = [OSError(f"fail-{i + 1}") for i in range(success_at - 1)]
            effects.append(None)  # success on attempt k
            puppet.connect = AsyncMock(side_effect=effects)
        else:
            puppet.connect = AsyncMock(side_effect=OSError("always-fail"))

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await manager._connect_puppet_with_backoff(puppet, max_attempts=max_attempts)

        if success_at is not None:
            # Should succeed after exactly k attempts
            assert result is True, f"Expected True for success_at={success_at}, max_attempts={max_attempts}"
            assert puppet.connect.await_count == success_at, (
                f"Expected {success_at} attempts, got {puppet.connect.await_count}"
            )
        else:
            # All attempts fail
            assert result is False, f"Expected False when all {max_attempts} attempts fail"
            assert puppet.connect.await_count == max_attempts, (
                f"Expected {max_attempts} attempts, got {puppet.connect.await_count}"
            )


class TestPuppetBackoffDelayBoundsProperty:
    """**Validates: Requirement 4.2**

    Property 6: Puppet backoff delay bounds
    For any attempt i in [0, max_attempts), base delay equals
    min(backoff_max, backoff_min * 2^i) and actual delay with jitter
    falls within [base * 0.5, base * 1.5].
    """

    @pytest.mark.asyncio
    @given(
        max_attempts=st.integers(min_value=2, max_value=10),
        backoff_min=st.floats(min_value=0.5, max_value=5.0),
        backoff_max=st.floats(min_value=5.0, max_value=60.0),
    )
    async def test_puppet_backoff_delay_bounds(self, max_attempts: int, backoff_min: float, backoff_max: float):
        """**Validates: Requirement 4.2**"""
        manager = _make_manager()
        puppet = _mock_puppet()

        # Always fail so all attempts are made and all delays captured
        puppet.connect = AsyncMock(side_effect=OSError("always-fail"))

        captured_delays: list[float] = []

        async def capture_sleep(delay: float) -> None:
            captured_delays.append(delay)

        with patch("asyncio.sleep", side_effect=capture_sleep):
            result = await manager._connect_puppet_with_backoff(
                puppet,
                max_attempts=max_attempts,
                backoff_min=backoff_min,
                backoff_max=backoff_max,
            )

        assert result is False

        # Sleep is called between attempts, so (max_attempts - 1) sleeps
        assert len(captured_delays) == max_attempts - 1, (
            f"Expected {max_attempts - 1} sleeps, got {len(captured_delays)}"
        )

        for i, delay in enumerate(captured_delays):
            base = min(backoff_max, backoff_min * (2**i))
            lo = base * 0.5
            hi = base * 1.5
            assert lo <= delay <= hi, (
                f"Attempt {i}: delay {delay:.4f} outside "
                f"[{lo:.4f}, {hi:.4f}] (base={base:.4f}, "
                f"backoff_min={backoff_min}, backoff_max={backoff_max})"
            )
