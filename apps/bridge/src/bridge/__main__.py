"""Bridge entrypoint. Loads config, starts gateway; adapters register in later phases."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any, Protocol

from loguru import logger

from bridge import __version__
from bridge.adapters.discord import DiscordAdapter
from bridge.adapters.irc import IRCAdapter
from bridge.adapters.xmpp import XMPPAdapter
from bridge.config import Config, cfg, load_config_with_env
from bridge.events import config_reload
from bridge.gateway import Bus, ChannelRouter, Relay
from bridge.gateway.msgid_resolver import DefaultMessageIDResolver
from bridge.identity import DevIdentityResolver, IdentityResolver, PortalClient


class Adapter(Protocol):
    """Protocol for adapters with start/stop methods."""

    async def start(self) -> None: ...
    async def stop(self) -> None: ...


# Third-party libraries to intercept and route through loguru
_INTERCEPTED_LIBRARIES = ["pydle", "pydle.client", "pydle.connection", "pydle.features.ircv3.cap"]


def _intercept_logging(level: str) -> None:
    """Route third-party library logs to loguru. Sets pydle to level for protocol debugging."""

    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            level_map = {
                "DEBUG": "DEBUG",
                "INFO": "INFO",
                "WARNING": "WARNING",
                "ERROR": "ERROR",
                "CRITICAL": "CRITICAL",
            }
            log_level = level_map.get(record.levelname, record.levelname)
            try:
                log_level = logger.level(log_level).name
            except ValueError:
                log_level = str(record.levelno)
            msg = record.getMessage().replace("{", "{{").replace("}", "}}")
            logger.patch(
                lambda r: r.update(
                    name=record.name,
                    function=record.funcName,
                    line=record.lineno,
                ),
            ).opt(exception=record.exc_info).log(log_level, msg)

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for lib in _INTERCEPTED_LIBRARIES:
        lib_logger = logging.getLogger(lib)
        lib_logger.handlers = [InterceptHandler()]
        lib_logger.propagate = False
        lib_logger.setLevel(level)


def _safe_message_filter(record: Any) -> bool:
    """Escape braces/angles in log messages to prevent format/tag errors."""
    if isinstance(record.get("message"), str):
        msg = record["message"]
        msg = msg.replace("{", "{{").replace("}", "}}").replace("<", "\\<")
        record["message"] = msg
    return True


def setup_logging(verbose: bool = False) -> None:
    """Configure loguru. Replace default logging.
    Level: verbose=True or LOG_LEVEL=DEBUG enables DEBUG; otherwise INFO.
    Intercepts pydle logs and routes them through loguru for protocol debugging."""
    level = "INFO"
    if verbose:
        level = "DEBUG"
    else:
        env_level = (os.environ.get("LOG_LEVEL") or "").upper()
        if env_level in ("DEBUG", "INFO", "WARNING", "ERROR"):
            level = env_level

    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format=("<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | {message}"),
        filter=_safe_message_filter,
    )
    _intercept_logging(level)


def reload_config(config_path: Path) -> Config:
    """Load config from path and update global cfg."""
    data = load_config_with_env(config_path)
    cfg.reload(data)
    return cfg


def main() -> None:
    """Main entrypoint."""
    parser = argparse.ArgumentParser(description="ATL Bridge — Discord–IRC–XMPP multi-presence bridge")
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=Path("config.yaml"),
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    args = parser.parse_args()

    setup_logging(args.verbose)

    if not args.config.exists():
        logger.error("Config file not found: {}", args.config)
        sys.exit(1)

    # Load config
    config = reload_config(args.config)
    logger.info("Config loaded from {}", args.config)

    # Create gateway components (before SIGHUP handler so it can use bus.publish)
    bus = Bus()
    router = ChannelRouter()
    router.load_from_config(config.raw)

    # SIGHUP reload — use bus.publish (AUDIT §5)
    def on_sighup(*a: object, **kw: object) -> None:
        config = reload_config(args.config)
        router.load_from_config(config.raw)
        _, evt = config_reload()
        bus.publish("main", evt)
        logger.info("Config reloaded (SIGHUP)")

    signal.signal(signal.SIGHUP, on_sighup)

    # Relay: MessageIn -> MessageOut for other protocols
    relay = Relay(bus, router)
    bus.register(relay)

    # Portal client + identity resolver (when Portal URL available)
    portal_url = _get_portal_url()
    identity_resolver: IdentityResolver | DevIdentityResolver | None = None
    if portal_url:
        client = PortalClient(portal_url, token=_get_portal_token())
        identity_resolver = IdentityResolver(
            client,
            ttl=config.identity_cache_ttl_seconds,
        )
        logger.info("Portal identity client configured: {}", portal_url)
    elif _dev_irc_puppets_enabled():
        identity_resolver = DevIdentityResolver()
        logger.info("Dev IRC puppets enabled (no Portal); nicks from BRIDGE_DEV_IRC_NICK_MAP or atl_dev_*")
    else:
        logger.warning("BRIDGE_PORTAL_BASE_URL not set; identity resolution disabled")

    logger.info(
        "Bridge ready — {} mappings",
        len(router.all_mappings()),
    )

    # Run async main (uvloop if available for better I/O throughput)
    try:
        import uvloop

        uvloop.run(_run(bus, router, identity_resolver))
    except ImportError:
        asyncio.run(_run(bus, router, identity_resolver))


def _get_portal_url() -> str | None:
    """Read Portal base URL from env."""
    import os

    return os.environ.get("BRIDGE_PORTAL_BASE_URL") or os.environ.get("BRIDGE_PORTAL_URL")


def _dev_irc_puppets_enabled() -> bool:
    """True when BRIDGE_DEV_IRC_PUPPETS is truthy (for local dev without Portal)."""
    import os

    return os.environ.get("BRIDGE_DEV_IRC_PUPPETS", "").lower() in ("1", "true", "yes")


def _get_portal_token() -> str | None:
    """Read Portal API token from env."""
    import os

    return os.environ.get("BRIDGE_PORTAL_TOKEN") or os.environ.get("BRIDGE_PORTAL_API_TOKEN")


async def _run(
    bus: Bus,
    router: ChannelRouter,
    identity_resolver: IdentityResolver | None,
) -> None:
    """Async run loop. Start adapters and wait."""
    msgid_resolver = DefaultMessageIDResolver()
    adapters: list[Adapter] = []
    discord_adapter = DiscordAdapter(bus, router, identity_resolver, msgid_resolver)
    irc_adapter = IRCAdapter(bus, router, identity_resolver, msgid_resolver)
    xmpp_adapter = XMPPAdapter(bus, router, identity_resolver, msgid_resolver)
    adapters.extend([discord_adapter, irc_adapter, xmpp_adapter])

    logger.info("Starting adapters")
    await discord_adapter.start()
    await irc_adapter.start()
    await xmpp_adapter.start()

    try:
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        logger.info("Bridge shutting down")
        for adapter in adapters:
            name = getattr(adapter, "name", adapter.__class__.__name__)
            logger.info("Stopping {} adapter", name)
            await adapter.stop()


if __name__ == "__main__":
    main()
