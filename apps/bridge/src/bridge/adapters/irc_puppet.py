"""IRC puppet manager: per-Discord-user IRC connections with idle timeout."""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import TYPE_CHECKING

import pydle
from loguru import logger

from bridge.formatting.irc_message_split import split_irc_message

if TYPE_CHECKING:
    from bridge.gateway import Bus, ChannelRouter
    from bridge.identity import IdentityResolver


class IRCPuppet(pydle.Client):
    """Single IRC puppet connection for a Discord user."""

    def __init__(
        self,
        nick: str,
        discord_id: str,
        ping_interval: int = 120,
        prejoin_commands: list[str] | None = None,
        **kwargs,
    ):
        super().__init__(nick, **kwargs)
        self.discord_id = discord_id
        self.last_activity = time.time()
        self._ping_interval = ping_interval
        self._prejoin_commands: list[str] = prejoin_commands or []
        self._pinger_task: asyncio.Task | None = None
        self._initial_nick = nick

    def touch(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()

    async def on_connect(self):
        """Handle connection: send pre-join commands and start pinger."""
        await super().on_connect()
        logger.debug("IRC puppet {} connected", self.nickname)

        for cmd in self._prejoin_commands:
            raw = cmd.replace("{nick}", self._initial_nick)
            await self.rawmsg(*raw.split(" ", 1) if " " in raw else [raw])

        if self._pinger_task:
            self._pinger_task.cancel()
        self._pinger_task = asyncio.create_task(self._pinger())

    async def _pinger(self) -> None:
        """Send PING every ping_interval seconds to keep connection alive."""
        while True:
            await asyncio.sleep(self._ping_interval)
            try:
                await self.rawmsg("PING", "keep-alive")
            except Exception:
                break


class IRCPuppetManager:
    """Manages multiple IRC puppet connections per Discord user."""

    def __init__(
        self,
        bus: Bus,
        router: ChannelRouter,
        identity: IdentityResolver,
        server: str,
        port: int,
        tls: bool,
        tls_verify: bool = True,
        idle_timeout_hours: int = 24,
        ping_interval: int = 120,
        prejoin_commands: list[str] | None = None,
    ):
        self._bus = bus
        self._router = router
        self._identity = identity
        self._server = server
        self._port = port
        self._tls = tls
        self._tls_verify = tls_verify
        self._idle_timeout = idle_timeout_hours * 3600
        self._ping_interval = ping_interval
        self._prejoin_commands: list[str] = prejoin_commands or []
        self._puppets: dict[str, IRCPuppet] = {}
        self._cleanup_task: asyncio.Task | None = None

    async def get_or_create_puppet(self, discord_id: str) -> IRCPuppet | None:
        """Get existing puppet or create new one for Discord user."""
        if discord_id in self._puppets:
            puppet = self._puppets[discord_id]
            puppet.touch()
            return puppet

        # Resolve IRC nick from Portal
        nick = await self._identity.discord_to_irc(discord_id)
        if not nick:
            logger.debug("No IRC nick for Discord user {}", discord_id)
            return None

        # Create and connect puppet
        puppet = IRCPuppet(
            nick,
            discord_id,
            ping_interval=self._ping_interval,
            prejoin_commands=self._prejoin_commands,
        )
        self._puppets[discord_id] = puppet

        try:
            await puppet.connect(
                hostname=self._server,
                port=self._port,
                tls=self._tls,
                tls_verify=self._tls_verify,
            )
            puppet.touch()
            logger.info("Created IRC puppet {} for Discord user {}", nick, discord_id)
            return puppet
        except Exception as exc:
            logger.exception("Failed to connect IRC puppet {}: {}", nick, exc)
            del self._puppets[discord_id]
            return None

    def get_puppet_nicks(self) -> set[str]:
        """Return set of current puppet nicks (for echo detection on main connection)."""
        return {p.nickname for p in self._puppets.values()}

    async def send_message(self, discord_id: str, channel: str, content: str):
        """Send message via puppet."""
        puppet = await self.get_or_create_puppet(discord_id)
        if not puppet:
            logger.debug("IRC puppet: no puppet for discord_id={}; message not sent", discord_id)
            return

        try:
            for chunk in split_irc_message(content, max_bytes=450):
                await puppet.message(channel, chunk)
            puppet.touch()
            logger.info("IRC puppet: sent to {} as {}", channel, puppet.nickname)
        except Exception as exc:
            logger.exception("Puppet send failed for {}: {}", discord_id, exc)

    async def join_channel(self, discord_id: str, channel: str):
        """Join channel with puppet."""
        puppet = await self.get_or_create_puppet(discord_id)
        if puppet and channel not in puppet.channels:
            await puppet.join(channel)
            puppet.touch()

    async def _cleanup_idle_puppets(self):
        """Periodically disconnect idle puppets."""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                now = time.time()
                to_remove = []

                for discord_id, puppet in self._puppets.items():
                    if now - puppet.last_activity > self._idle_timeout:
                        to_remove.append(discord_id)

                for discord_id in to_remove:
                    puppet = self._puppets.pop(discord_id)
                    await puppet.disconnect()
                    logger.info("Disconnected idle IRC puppet for {}", discord_id)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("Puppet cleanup error: {}", exc)

    async def start(self):
        """Start cleanup task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_idle_puppets())

    async def stop(self):
        """Stop all puppets."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task

        for puppet in list(self._puppets.values()):
            await puppet.disconnect()
        self._puppets.clear()
