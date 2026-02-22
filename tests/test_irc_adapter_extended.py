"""Tests for IRC adapter / IRCClient uncovered branches: CHGHOST, SETNAME, SASL start."""

from __future__ import annotations

import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bridge.adapters.irc import IRCAdapter, IRCClient
from bridge.events import MessageOut
from bridge.gateway import Bus, ChannelRouter
from bridge.gateway.router import ChannelMapping, IrcTarget

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _irc_mapping(discord_id: str = "111", channel: str = "#test") -> ChannelMapping:
    return ChannelMapping(
        discord_channel_id=discord_id,
        irc=IrcTarget(server="irc.libera.chat", port=6697, tls=True, channel=channel),
        xmpp=None,
    )


def _make_adapter(identity_nick=None):
    bus = MagicMock(spec=Bus)
    router = MagicMock(spec=ChannelRouter)
    identity = AsyncMock()
    identity.discord_to_irc = AsyncMock(return_value=identity_nick)
    identity.has_irc = AsyncMock(return_value=True)
    adapter = IRCAdapter(bus, router, identity_resolver=identity)
    return adapter, bus, router


def _mock_client():
    c = MagicMock()
    c.rawmsg = AsyncMock()
    c.queue_message = MagicMock()
    c._typing_last = 0
    return c


# ---------------------------------------------------------------------------
# IRCClient.on_raw_chghost
# ---------------------------------------------------------------------------


class TestOnRawChghost:
    @pytest.mark.asyncio
    async def test_chghost_with_two_params_logs(self):
        """on_raw_chghost with two parameters should not raise."""
        client = object.__new__(IRCClient)
        client._server = "irc.libera.chat"

        msg = MagicMock()
        msg.source = "nick!user@host"
        msg.params = ["new_user", "new_host"]
        await client.on_raw_chghost(msg)

    @pytest.mark.asyncio
    async def test_chghost_with_one_param_does_not_raise(self):
        client = object.__new__(IRCClient)
        client._server = "irc.libera.chat"

        msg = MagicMock()
        msg.source = "nick!user@host"
        msg.params = ["only_user"]
        await client.on_raw_chghost(msg)  # len(params) < 2, should skip silently


# ---------------------------------------------------------------------------
# IRCClient.on_raw_setname
# ---------------------------------------------------------------------------


class TestOnRawSetname:
    @pytest.mark.asyncio
    async def test_setname_with_params_logs(self):
        client = object.__new__(IRCClient)

        msg = MagicMock()
        msg.source = "nick!user@host"
        msg.params = ["New Real Name"]
        await client.on_raw_setname(msg)

    @pytest.mark.asyncio
    async def test_setname_with_empty_params_does_not_raise(self):
        client = object.__new__(IRCClient)

        msg = MagicMock()
        msg.source = "nick!user@host"
        msg.params = []
        await client.on_raw_setname(msg)  # no params, should skip silently


# ---------------------------------------------------------------------------
# IRCAdapter.start — SASL kwargs injection
# ---------------------------------------------------------------------------


class TestStartSasl:
    @pytest.mark.asyncio
    async def test_start_injects_sasl_kwargs_when_configured(self):
        adapter, _bus, router = _make_adapter()
        router.all_mappings.return_value = [_irc_mapping()]

        mock_puppet_mgr = AsyncMock()
        mock_puppet_mgr.start = AsyncMock()

        async def _fake_backoff(client, hostname, port, tls):
            await asyncio.sleep(9999)

        with (
            patch("bridge.adapters.irc.IRCClient") as mock_irc_cls,
            patch("bridge.adapters.irc._connect_with_backoff", side_effect=_fake_backoff),
            patch("bridge.adapters.irc.IRCPuppetManager", return_value=mock_puppet_mgr),
            patch("bridge.adapters.irc.cfg") as mock_cfg,
            patch.dict("os.environ", {"IRC_NICK": "bot"}),
        ):
            mock_cfg.irc_use_sasl = True
            mock_cfg.irc_sasl_user = "sasluser"
            mock_cfg.irc_sasl_password = "saslpass"
            mock_cfg.irc_throttle_limit = 10
            mock_cfg.irc_rejoin_delay = 5.0
            mock_cfg.irc_auto_rejoin = True
            mock_cfg.irc_puppet_ping_interval = 120
            mock_cfg.irc_puppet_prejoin_commands = []
            mock_irc_cls.return_value = MagicMock()

            await adapter.start()

            call_kwargs = mock_irc_cls.call_args[1]
            assert call_kwargs.get("sasl_username") == "sasluser"
            assert call_kwargs.get("sasl_password") == "saslpass"

        # cancel the background task
        if adapter._task:
            adapter._task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await adapter._task

    @pytest.mark.asyncio
    async def test_start_no_sasl_when_disabled(self):
        adapter, _bus, router = _make_adapter()
        router.all_mappings.return_value = [_irc_mapping()]

        mock_puppet_mgr = AsyncMock()
        mock_puppet_mgr.start = AsyncMock()

        async def _fake_backoff(client, hostname, port, tls):
            await asyncio.sleep(9999)

        with (
            patch("bridge.adapters.irc.IRCClient") as mock_irc_cls,
            patch("bridge.adapters.irc._connect_with_backoff", side_effect=_fake_backoff),
            patch("bridge.adapters.irc.IRCPuppetManager", return_value=mock_puppet_mgr),
            patch("bridge.adapters.irc.cfg") as mock_cfg,
            patch.dict("os.environ", {"IRC_NICK": "bot"}),
        ):
            mock_cfg.irc_use_sasl = False
            mock_cfg.irc_sasl_user = ""
            mock_cfg.irc_sasl_password = ""
            mock_cfg.irc_throttle_limit = 10
            mock_cfg.irc_rejoin_delay = 5.0
            mock_cfg.irc_auto_rejoin = True
            mock_cfg.irc_puppet_ping_interval = 120
            mock_cfg.irc_puppet_prejoin_commands = []
            mock_irc_cls.return_value = MagicMock()

            await adapter.start()

            call_kwargs = mock_irc_cls.call_args[1]
            assert "sasl_username" not in call_kwargs
            assert "sasl_password" not in call_kwargs

        if adapter._task:
            adapter._task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await adapter._task


# ---------------------------------------------------------------------------
# IRCAdapter._send_typing — throttle hit path
# ---------------------------------------------------------------------------


class TestSendTypingThrottle:
    @pytest.mark.asyncio
    async def test_throttle_hit_does_not_send(self):
        """If typing was sent < 3s ago, rawmsg is not called."""
        import time

        adapter, _, router = _make_adapter()
        adapter._client = _mock_client()
        # Simulate just-sent typing
        adapter._client._typing_last = time.time()
        router.get_mapping_for_discord.return_value = _irc_mapping()

        from bridge.events import TypingOut

        evt = TypingOut(target_origin="irc", channel_id="111")
        await adapter._send_typing(evt)
        adapter._client.rawmsg.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_throttle_updates_after_send(self):
        """After sending, _typing_last should be updated."""
        import time

        adapter, _, router = _make_adapter()
        adapter._client = _mock_client()
        adapter._client._typing_last = 0
        router.get_mapping_for_discord.return_value = _irc_mapping()

        from bridge.events import TypingOut

        evt = TypingOut(target_origin="irc", channel_id="111")
        before = time.time()
        await adapter._send_typing(evt)
        assert adapter._client._typing_last >= before


# ---------------------------------------------------------------------------
# IRCAdapter._send_via_puppet — fallback when has_irc is False
# ---------------------------------------------------------------------------


class TestSendViaPuppetFallback:
    @pytest.mark.asyncio
    async def test_falls_back_to_client_when_no_irc_identity(self):
        adapter, _, router = _make_adapter()
        adapter._puppet_manager = AsyncMock()
        adapter._client = _mock_client()
        adapter._identity.has_irc = AsyncMock(return_value=False)  # type: ignore[union-attr]
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
        adapter._client.queue_message.assert_called_once_with(evt)  # type: ignore[union-attr]
        adapter._puppet_manager.send_message.assert_not_awaited()


# ---------------------------------------------------------------------------
# AdapterBase default method coverage
# ---------------------------------------------------------------------------


class TestAdapterBase:
    def test_accept_event_default_returns_false(self):
        from bridge.adapters.base import AdapterBase

        class ConcreteAdapter(AdapterBase):
            @property
            def name(self) -> str:
                return "test"

            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass

        adapter = ConcreteAdapter()
        assert adapter.accept_event("source", object()) is False

    def test_push_event_default_is_noop(self):
        from bridge.adapters.base import AdapterBase

        class ConcreteAdapter(AdapterBase):
            @property
            def name(self) -> str:
                return "test"

            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass

        adapter = ConcreteAdapter()
        # Should not raise and return None
        result = adapter.push_event("source", object())
        assert result is None
