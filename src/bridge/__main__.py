"""Bridge entrypoint. Loads config, starts gateway; adapters register in later phases."""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from pathlib import Path

from loguru import logger

from bridge import __version__
from bridge.adapters.disc import DiscordAdapter
from bridge.adapters.irc import IRCAdapter
from bridge.adapters.xmpp import XMPPAdapter
from bridge.config import Config, cfg, load_config_with_env
from bridge.events import config_reload, dispatcher
from bridge.gateway import Bus, ChannelRouter, Relay
from bridge.identity import IdentityResolver, PortalClient


def setup_logging(verbose: bool = False) -> None:
    """Configure loguru. Replace default logging."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG" if verbose else "INFO",
        format=(
            "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
            "<cyan>{name}</cyan> | {message}"
        ),
    )


def reload_config(config_path: Path) -> Config:
    """Load config from path and update global cfg."""
    data = load_config_with_env(config_path)
    cfg.reload(data)
    return cfg


def main() -> None:
    """Main entrypoint."""
    parser = argparse.ArgumentParser(
        description="ATL Bridge — Discord–IRC–XMPP multi-presence bridge"
    )
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

    # SIGHUP reload
    def on_sighup(*a: object, **kw: object) -> None:
        reload_config(args.config)
        _, evt = config_reload()
        dispatcher.dispatch("main", evt)
        logger.info("Config reloaded (SIGHUP)")

    signal.signal(signal.SIGHUP, on_sighup)

    # Create gateway components
    bus = Bus()
    router = ChannelRouter()
    router.load_from_config(config.raw)

    # Relay: MessageIn -> MessageOut for other protocols
    relay = Relay(bus, router)
    bus.register(relay)

    # Portal client + identity resolver (when Portal URL available)
    portal_url = _get_portal_url()
    identity_resolver: IdentityResolver | None = None
    if portal_url:
        client = PortalClient(portal_url, token=_get_portal_token())
        identity_resolver = IdentityResolver(
            client,
            ttl=config.identity_cache_ttl_seconds,
        )
        logger.info("Portal identity client configured: {}", portal_url)
    else:
        logger.warning("PORTAL_BASE_URL not set; identity resolution disabled")

    logger.info(
        "Bridge ready — {} mappings",
        len(router.all_mappings()),
    )

    # Run async main
    asyncio.run(_run(bus, router, identity_resolver))


def _get_portal_url() -> str | None:
    """Read Portal base URL from env."""
    import os

    return os.environ.get("PORTAL_BASE_URL") or os.environ.get("PORTAL_URL")


def _get_portal_token() -> str | None:
    """Read Portal API token from env."""
    import os

    return os.environ.get("PORTAL_TOKEN") or os.environ.get("PORTAL_API_TOKEN")


async def _run(
    bus: Bus,
    router: ChannelRouter,
    identity_resolver: IdentityResolver | None,
) -> None:
    """Async run loop. Start adapters and wait."""
    adapters: list[object] = []
    discord_adapter = DiscordAdapter(bus, router, identity_resolver)
    irc_adapter = IRCAdapter(bus, router, identity_resolver)
    xmpp_adapter = XMPPAdapter(bus, router, identity_resolver)
    adapters.extend([discord_adapter, irc_adapter, xmpp_adapter])
    await discord_adapter.start()
    await irc_adapter.start()
    await xmpp_adapter.start()

    try:
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        logger.info("Bridge shutting down")
        for adapter in adapters:
            if hasattr(adapter, "stop"):
                await adapter.stop()


if __name__ == "__main__":
    main()
