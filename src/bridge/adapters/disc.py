"""Discord adapter: bot, webhooks per identity, queue for outbound (AUDIT §2)."""

from __future__ import annotations

import asyncio
import contextlib
import os
import re
from typing import TYPE_CHECKING

from discord import Intents, Message
from discord.ext import commands
from discord.webhook import Webhook
from loguru import logger

from bridge.events import MessageOut, message_in
from bridge.gateway import Bus, ChannelRouter

if TYPE_CHECKING:
    from bridge.identity import IdentityResolver

# Webhook username: 2-32 chars (AUDIT §3)
MIN_USERNAME_LEN = 2
MAX_USERNAME_LEN = 32


def _ensure_valid_username(name: str) -> str:
    """Truncate or pad username to fit Discord webhook limits."""
    name = str(name)[:MAX_USERNAME_LEN]
    if len(name) < MIN_USERNAME_LEN:
        name = name + "_" * (MIN_USERNAME_LEN - len(name))
    return name


def _strip_everyone_here(content: str) -> str:
    """Strip @everyone and @here to avoid accidental pings (AUDIT §3)."""
    return re.sub(r"@(everyone|here)\b", r"@\1", content)


class DiscordAdapter:
    """Discord adapter: receives messages, sends via webhooks with queue."""

    def __init__(
        self,
        bus: Bus,
        router: ChannelRouter,
        identity_resolver: IdentityResolver | None,
    ) -> None:
        self._bus = bus
        self._router = router
        self._identity = identity_resolver
        self._queue: asyncio.Queue[MessageOut] = asyncio.Queue()
        self._webhook_cache: dict[tuple[str, str], Webhook] = {}
        self._bot: commands.Bot | None = None
        self._consumer_task: asyncio.Task | None = None
        self._bot_task: asyncio.Task | None = None

    @property
    def name(self) -> str:
        return "discord"

    def accept_event(self, source: str, evt: object) -> bool:
        """Accept MessageOut targeting Discord."""
        return isinstance(evt, MessageOut) and evt.target_origin == "discord"

    def push_event(self, source: str, evt: object) -> None:
        """Queue MessageOut for webhook send."""
        if isinstance(evt, MessageOut):
            self._queue.put_nowait(evt)

    async def _webhook_send(
        self,
        channel_id: str,
        author_display: str,
        content: str,
        *,
        avatar_url: str | None = None,
    ) -> None:
        """Send message via webhook. Creates or reuses webhook per identity."""
        bot = self._bot
        if not bot:
            return

        channel = bot.get_channel(int(channel_id))
        if not channel:
            logger.warning("Discord channel {} not found", channel_id)
            return

        cache_key = (channel_id, author_display)
        webhook = self._webhook_cache.get(cache_key)

        if not webhook:
            # Create webhook on first use (or fetch existing)
            try:
                webhooks = await channel.webhooks()
                for wh in webhooks:
                    if wh.name == author_display[:80]:  # Webhook name limit
                        webhook = wh
                        break
                if not webhook and len(webhooks) < 15:
                    webhook = await channel.create_webhook(
                        name=_ensure_valid_username(author_display)[:32],
                        reason="ATL Bridge relay",
                    )
                if webhook:
                    self._webhook_cache[cache_key] = webhook
            except Exception as exc:
                logger.exception("Failed to get/create webhook for {}: {}", cache_key, exc)
                return

        if not webhook:
            logger.warning("No webhook available for {} (limit 15/channel?)", cache_key)
            return

        content = _strip_everyone_here(content)
        await webhook.send(
            content=content[:2000],
            username=_ensure_valid_username(author_display),
            avatar_url=avatar_url,
            wait=True,
        )

    async def _queue_consumer(self, delay: float = 0.25) -> None:
        """Background consumer: pop from queue, send via webhook with delay (AUDIT §3)."""
        while True:
            try:
                evt = await self._queue.get()
                await self._webhook_send(
                    evt.channel_id,
                    evt.author_display,
                    evt.content,
                    avatar_url=evt.raw.get("avatar_url"),
                )
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("Webhook send failed: {}", exc)

    def _is_bridged_channel(self, channel_id: str) -> bool:
        return self._router.get_mapping_for_discord(str(channel_id)) is not None

    async def _on_message(self, message: Message) -> None:
        """Handle incoming Discord message; emit MessageIn to bus."""
        if message.author.bot:
            return

        channel_id = str(message.channel.id)
        if not self._is_bridged_channel(channel_id):
            return

        content = message.content or ""
        if not content.strip():
            return

        _, evt = message_in(
            origin="discord",
            channel_id=channel_id,
            author_id=str(message.author.id),
            author_display=message.author.display_name or message.author.name,
            content=content,
            message_id=str(message.id),
            reply_to_id=str(message.reference.message_id) if message.reference else None,
            is_edit=False,
            is_action=False,
            raw={},
        )
        self._bus.publish("discord", evt)

    async def _cmd_bridge_status(self, ctx: commands.Context) -> None:
        """Optional !bridge status: show linked IRC/XMPP (AUDIT §7)."""
        if not ctx.guild or not ctx.author:
            return

        if not self._identity:
            await ctx.reply("Identity resolution not configured (Portal).")
            return

        discord_id = str(ctx.author.id)
        irc_nick = await self._identity.discord_to_irc(discord_id)
        xmpp_jid = await self._identity.discord_to_xmpp(discord_id)

        parts = []
        if irc_nick:
            parts.append(f"IRC: {irc_nick}")
        else:
            parts.append("IRC: not linked")
        if xmpp_jid:
            parts.append(f"XMPP: {xmpp_jid}")
        else:
            parts.append("XMPP: not linked")

        await ctx.reply(" | ".join(parts))

    async def start(self) -> None:
        """Start Discord bot and queue consumer."""
        token = os.environ.get("DISCORD_TOKEN")
        if not token:
            logger.warning("DISCORD_TOKEN not set; Discord adapter disabled")
            return

        intents = Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        bot = commands.Bot(command_prefix="!", intents=intents)

        @bot.event
        async def on_ready() -> None:
            logger.info("Discord bot ready: {}", bot.user)

        @bot.event
        async def on_message(message: Message) -> None:
            if message.content and message.content.strip().startswith("!bridge"):
                await bot.process_commands(message)
                return
            await self._on_message(message)

        @bot.command(name="bridge")
        async def cmd_bridge(ctx: commands.Context, *args: str) -> None:
            """!bridge or !bridge status: show linked IRC/XMPP accounts."""
            await self._cmd_bridge_status(ctx)

        self._bot = bot
        self._consumer_task = asyncio.create_task(self._queue_consumer())
        self._bot_task = asyncio.create_task(bot.start(token))

        self._bus.register(self)

    async def stop(self) -> None:
        """Stop Discord bot and consumer."""
        self._bus.unregister(self)
        if self._consumer_task:
            self._consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._consumer_task
        if self._bot:
            await self._bot.close()
        if self._bot_task:
            self._bot_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._bot_task
        self._bot = None
        self._bot_task = None
