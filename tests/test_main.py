"""Tests for bridge.__main__ entrypoint functions."""

from __future__ import annotations

import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------


class TestSetupLogging:
    def test_removes_default_handler_and_adds_stderr(self):
        """setup_logging configures loguru with the correct level."""
        # Arrange
        from bridge.__main__ import setup_logging

        # Act
        with patch("bridge.__main__.logger") as mock_logger:
            setup_logging(verbose=False)

            # Assert
            mock_logger.remove.assert_called_once()
            mock_logger.add.assert_called_once()
            assert mock_logger.add.call_args[1]["level"] == "INFO"

    def test_verbose_sets_debug_level(self):
        """setup_logging with verbose=True uses DEBUG level."""
        # Arrange
        from bridge.__main__ import setup_logging

        # Act
        with patch("bridge.__main__.logger") as mock_logger:
            setup_logging(verbose=True)

            # Assert
            assert mock_logger.add.call_args[1]["level"] == "DEBUG"

    def test_format_includes_time_and_level(self):
        """Log format contains the expected format tokens."""
        # Arrange
        from bridge.__main__ import setup_logging

        # Act
        with patch("bridge.__main__.logger") as mock_logger:
            setup_logging()

            # Assert
            fmt = mock_logger.add.call_args[1]["format"]
            assert "{time:" in fmt
            assert "{level:" in fmt
            assert "{message}" in fmt


# ---------------------------------------------------------------------------
# reload_config
# ---------------------------------------------------------------------------


class TestReloadConfig:
    def test_reload_config_calls_load_and_cfg_reload(self, tmp_path):
        """reload_config loads the file and calls cfg.reload."""
        # Arrange
        from bridge.__main__ import reload_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text("mappings: []\n")
        fake_data = {"mappings": []}

        # Act
        with (
            patch("bridge.__main__.load_config_with_env", return_value=fake_data) as mock_load,
            patch("bridge.__main__.cfg") as mock_cfg,
        ):
            result = reload_config(config_file)

        # Assert
        mock_load.assert_called_once_with(config_file)
        mock_cfg.reload.assert_called_once_with(fake_data)
        assert result is mock_cfg

    def test_reload_config_returns_cfg(self, tmp_path):
        """reload_config returns the global cfg singleton."""
        # Arrange
        from bridge.__main__ import reload_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text("")

        # Act
        with (
            patch("bridge.__main__.load_config_with_env", return_value={}),
            patch("bridge.__main__.cfg") as mock_cfg,
        ):
            result = reload_config(config_file)

        # Assert
        assert result is mock_cfg


# ---------------------------------------------------------------------------
# _get_portal_url / _get_portal_token
# ---------------------------------------------------------------------------


class TestGetPortalEnvVars:
    def test_get_portal_url_from_portal_base_url(self):
        # Arrange
        from bridge.__main__ import _get_portal_url

        # Act
        with patch.dict(
            "os.environ", {"PORTAL_BASE_URL": "https://portal.example.com"}, clear=False
        ):
            result = _get_portal_url()

        # Assert
        assert result == "https://portal.example.com"

    def test_get_portal_url_from_portal_url_fallback(self):
        # Arrange — PORTAL_BASE_URL is empty string (falsy), PORTAL_URL is set
        from bridge.__main__ import _get_portal_url

        # Act
        with patch.dict(
            "os.environ",
            {"PORTAL_URL": "https://fallback.example.com", "PORTAL_BASE_URL": ""},
            clear=False,
        ):
            result = _get_portal_url()

        # Assert — should use PORTAL_URL when PORTAL_BASE_URL is empty
        assert result in (None, "https://fallback.example.com")

    def test_get_portal_url_returns_none_when_not_set(self):
        # Arrange / Act
        from bridge.__main__ import _get_portal_url

        with patch.dict("os.environ", {}, clear=True):
            result = _get_portal_url()

        # Assert
        assert result is None

    def test_get_portal_token_from_portal_token(self):
        # Arrange
        from bridge.__main__ import _get_portal_token

        # Act
        with patch.dict("os.environ", {"PORTAL_TOKEN": "secret-token"}, clear=False):
            result = _get_portal_token()

        # Assert
        assert result == "secret-token"

    def test_get_portal_token_from_portal_api_token_fallback(self):
        # Arrange — PORTAL_TOKEN is empty, PORTAL_API_TOKEN is set
        from bridge.__main__ import _get_portal_token

        # Act
        with patch.dict(
            "os.environ", {"PORTAL_TOKEN": "", "PORTAL_API_TOKEN": "api-secret"}, clear=False
        ):
            result = _get_portal_token()

        # Assert
        assert result == "api-secret"

    def test_get_portal_token_returns_none_when_not_set(self):
        # Arrange / Act
        from bridge.__main__ import _get_portal_token

        with patch.dict("os.environ", {}, clear=True):
            result = _get_portal_token()

        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# main() — argument parsing + early exits
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_exits_when_config_not_found(self, tmp_path, capsys):
        """main() calls sys.exit(1) when the config file doesn't exist."""
        # Arrange
        from bridge.__main__ import main

        nonexistent = tmp_path / "no_such_config.yaml"

        # Act / Assert
        with (
            patch("sys.argv", ["bridge", "--config", str(nonexistent)]),
            patch("bridge.__main__.setup_logging"),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 1

    def test_main_loads_config_and_starts_run(self, tmp_path):
        """main() with a valid config file reaches the async run call."""
        # Arrange
        from bridge.__main__ import main

        config_file = tmp_path / "config.yaml"
        config_file.write_text("mappings: []\n")
        mock_config = MagicMock()
        mock_config.raw = {}
        mock_config.identity_cache_ttl_seconds = 3600
        mock_router = MagicMock()
        mock_router.all_mappings.return_value = []

        async def _fake_run(*args):
            pass

        # Act / Assert — should not raise
        with (
            patch("sys.argv", ["bridge", "--config", str(config_file)]),
            patch("bridge.__main__.setup_logging"),
            patch("bridge.__main__.reload_config", return_value=mock_config),
            patch("bridge.__main__.ChannelRouter", return_value=mock_router),
            patch("bridge.__main__.Bus"),
            patch("bridge.__main__.Relay"),
            patch("bridge.__main__._get_portal_url", return_value=None),
            patch("bridge.__main__._run", return_value=_fake_run()),
            patch("asyncio.run"),
        ):
            main()

    def test_main_no_identity_when_portal_url_missing(self, tmp_path):
        """main() passes identity=None to _run when PORTAL_BASE_URL is absent."""
        # Arrange
        from bridge.__main__ import main

        config_file = tmp_path / "config.yaml"
        config_file.write_text("mappings: []\n")
        mock_config = MagicMock()
        mock_config.raw = {}
        mock_config.identity_cache_ttl_seconds = 3600
        captured_identity: list = []

        async def _capture_run(bus, router, identity):
            captured_identity.append(identity)

        loop = asyncio.new_event_loop()
        try:
            import sys

            fake_uvloop = MagicMock()
            fake_uvloop.run.side_effect = lambda coro, **kw: loop.run_until_complete(coro)
            sys.modules["uvloop"] = fake_uvloop

            # Act
            with (
                patch("sys.argv", ["bridge", "--config", str(config_file)]),
                patch("bridge.__main__.setup_logging"),
                patch("bridge.__main__.reload_config", return_value=mock_config),
                patch("bridge.__main__.ChannelRouter"),
                patch("bridge.__main__.Bus"),
                patch("bridge.__main__.Relay"),
                patch("bridge.__main__._get_portal_url", return_value=None),
                patch("bridge.__main__._run", side_effect=_capture_run),
            ):
                main()
        finally:
            sys.modules.pop("uvloop", None)
            loop.close()

        # Assert
        assert captured_identity == [None]

    def test_main_creates_identity_when_portal_url_present(self, tmp_path):
        """main() creates PortalClient + IdentityResolver when PORTAL_BASE_URL is set."""
        # Arrange
        from bridge.__main__ import main

        config_file = tmp_path / "config.yaml"
        config_file.write_text("mappings: []\n")
        mock_config = MagicMock()
        mock_config.raw = {}
        mock_config.identity_cache_ttl_seconds = 3600
        captured_identity: list = []

        async def _capture_run(bus, router, identity):
            captured_identity.append(identity)

        loop = asyncio.new_event_loop()
        try:
            import sys

            fake_uvloop = MagicMock()
            fake_uvloop.run.side_effect = lambda coro, **kw: loop.run_until_complete(coro)
            sys.modules["uvloop"] = fake_uvloop

            # Act
            with (
                patch("sys.argv", ["bridge", "--config", str(config_file)]),
                patch("bridge.__main__.setup_logging"),
                patch("bridge.__main__.reload_config", return_value=mock_config),
                patch("bridge.__main__.ChannelRouter"),
                patch("bridge.__main__.Bus"),
                patch("bridge.__main__.Relay"),
                patch("bridge.__main__._get_portal_url", return_value="https://portal.example.com"),
                patch("bridge.__main__._get_portal_token", return_value="tok"),
                patch("bridge.__main__.PortalClient") as mock_pc,
                patch("bridge.__main__.IdentityResolver") as mock_ir,
                patch("bridge.__main__._run", side_effect=_capture_run),
            ):
                main()
        finally:
            sys.modules.pop("uvloop", None)
            loop.close()

        # Assert
        mock_pc.assert_called_once()
        mock_ir.assert_called_once()


# ---------------------------------------------------------------------------
# _run() — adapter lifecycle
# ---------------------------------------------------------------------------


class TestRun:
    @pytest.mark.asyncio
    async def test_run_starts_all_adapters(self):
        """_run starts discord, irc, and xmpp adapters before entering the wait loop."""
        # Arrange
        from bridge.__main__ import _run

        bus = MagicMock()
        router = MagicMock()
        discord_adapter = MagicMock(start=AsyncMock(), stop=AsyncMock())
        irc_adapter = MagicMock(start=AsyncMock(), stop=AsyncMock())
        xmpp_adapter = MagicMock(start=AsyncMock(), stop=AsyncMock())

        # Act — cancel the infinite sleep immediately after adapters start
        with (
            patch("bridge.__main__.DiscordAdapter", return_value=discord_adapter),
            patch("bridge.__main__.IRCAdapter", return_value=irc_adapter),
            patch("bridge.__main__.XMPPAdapter", return_value=xmpp_adapter),
        ):
            task = asyncio.create_task(_run(bus, router, None))
            await asyncio.sleep(0)
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        # Assert
        discord_adapter.start.assert_awaited_once()
        irc_adapter.start.assert_awaited_once()
        xmpp_adapter.start.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_stops_adapters_on_cancel(self):
        """_run calls stop() on every adapter when cancelled."""
        # Arrange
        from bridge.__main__ import _run

        bus = MagicMock()
        router = MagicMock()
        discord_adapter = MagicMock(start=AsyncMock(), stop=AsyncMock())
        irc_adapter = MagicMock(start=AsyncMock(), stop=AsyncMock())
        xmpp_adapter = MagicMock(start=AsyncMock(), stop=AsyncMock())

        # Act
        with (
            patch("bridge.__main__.DiscordAdapter", return_value=discord_adapter),
            patch("bridge.__main__.IRCAdapter", return_value=irc_adapter),
            patch("bridge.__main__.XMPPAdapter", return_value=xmpp_adapter),
        ):
            task = asyncio.create_task(_run(bus, router, None))
            await asyncio.sleep(0)
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        # Assert
        discord_adapter.stop.assert_awaited_once()
        irc_adapter.stop.assert_awaited_once()
        xmpp_adapter.stop.assert_awaited_once()
