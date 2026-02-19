"""Discord adapter: bot, webhooks per identity, queue for outbound (AUDIT §2)."""

from __future__ import annotations

import asyncio
import contextlib
import io
import os
import re
from typing import TYPE_CHECKING

import aiohttp
from discord import File, Intents, Message, TextChannel
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
        if not channel or not isinstance(channel, TextChannel):
            logger.warning("Discord channel {} not found or not a text channel", channel_id)
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
                evt = await self._outbound.get()  # type: ignore[attr-defined]

                # Check if this is an edit
                is_edit = evt.raw.get("is_edit", False)
                replace_id = evt.raw.get("replace_id")

                if is_edit and replace_id and self._bot:
                    # Handle XMPP correction -> Discord edit
                    # Look up Discord message ID from XMPP message ID
                    # This requires the XMPP component's tracker, which we don't have direct access to
                    # For now, log that we received an edit
                    logger.debug("Received edit from XMPP (replace_id: {}), but Discord edit not yet implemented", replace_id)
                    # TODO: Implement Discord message editing via bot API

                # Send as new message (or edit if implemented above)
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

    async def _handle_attachments(self, message: Message) -> None:
        """Download Discord attachments and send via XMPP HTTP upload."""
        if not self._identity:
            return

        channel_id = str(message.channel.id)
        mapping = self._router.get_mapping_for_discord(channel_id)
        if not mapping:
            return

        discord_id = str(message.author.id)

        # Send to XMPP via HTTP upload if configured
        if mapping.xmpp:
            nick = await self._identity.discord_to_xmpp(discord_id)
            if nick:
                from bridge.adapters.xmpp import XMPPAdapter

                xmpp_adapter = None
                for adapter in self._bus._adapters:  # type: ignore[attr-defined]
                    if isinstance(adapter, XMPPAdapter):
                        xmpp_adapter = adapter
                        break

                if xmpp_adapter and xmpp_adapter._component:
                    for attachment in message.attachments:
                        if attachment.size > 10 * 1024 * 1024:
                            continue

                        try:
                            async with aiohttp.ClientSession() as session, session.get(attachment.url) as resp:
                                if resp.status == 200:
                                    data = await resp.read()
                                    await xmpp_adapter._component.send_file_with_fallback(
                                        discord_id,
                                        mapping.xmpp.muc_jid,
                                        data,
                                        attachment.filename,
                                        nick,
                                    )
                                    logger.info(
                                            "Sent Discord attachment {} to XMPP",
                                            attachment.filename,
                                        )
                        except Exception as exc:
                            logger.exception("Failed to bridge attachment to XMPP: {}", exc)

        # Send to IRC as URL notification
        if mapping.irc:
            for attachment in message.attachments:
                file_info = f"📎 {attachment.filename} ({attachment.size} bytes): {attachment.url}"
                _, evt = message_in(
                    origin="discord",
                    channel_id=channel_id,
                    author_id=discord_id,
                    author_display=message.author.display_name or message.author.name,
                    content=file_info,
                    message_id=f"{message.id}_attachment_{attachment.id}",
                    is_action=False,
                    avatar_url=None,
                    raw={},
                )
                self._bus.publish("discord", evt)

    async def upload_file(self, channel_id: str, data: bytes, filename: str) -> None:
        """Upload file to Discord channel."""
        if not self._bot:
            return

        channel = self._bot.get_channel(int(channel_id))
        if not channel or not isinstance(channel, TextChannel):
            logger.warning("Discord channel {} not found", channel_id)
            return

        try:
            file_obj = File(io.BytesIO(data), filename=filename)
            await channel.send(file=file_obj)
            logger.info("Uploaded {} ({} bytes) to Discord", filename, len(data))
        except Exception as exc:
            logger.exception("Failed to upload file to Discord: {}", exc)

    async def _on_message(self, message: Message) -> None:
        """Handle incoming Discord message; emit MessageIn to bus."""
        if message.author.bot:
            return

        channel_id = str(message.channel.id)
        if not self._is_bridged_channel(channel_id):
            return

        content = message.content or ""

        # Handle attachments
        if message.attachments:
            await self._handle_attachments(message)
            if not content.strip():
                return

        if not content.strip():
            return

        # Get avatar URL
        avatar_url = str(message.author.display_avatar.url) if message.author.display_avatar else None

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
            avatar_url=avatar_url,
            raw={},
        )
        self._bus.publish("discord", evt)

    async def _on_message_edit(self, before: Message, after: Message) -> None:
        """Handle Discord message edits; emit MessageIn with is_edit=True."""
        if after.author.bot:
            return

        channel_id = str(after.channel.id)
        if not self._is_bridged_channel(channel_id):
            return

        content = after.content or ""
        if not content.strip():
            return

        # Get avatar URL
        avatar_url = str(after.author.display_avatar.url) if after.author.display_avatar else None

        _, evt = message_in(
            origin="discord",
            channel_id=channel_id,
            author_id=str(after.author.id),
            author_display=after.author.display_name or after.author.name,
            content=content,
            message_id=str(after.id),
            reply_to_id=str(after.reference.message_id) if after.reference else None,
            is_edit=True,
            is_action=False,
            avatar_url=avatar_url,
            raw={},
        )
        self._bus.publish("discord", evt)

    async def _on_reaction_add(self, payload) -> None:
        """Handle Discord reaction add; send to XMPP."""
        if not self._identity:
            return

        channel_id = str(payload.channel_id)
        mapping = self._router.get_mapping_for_discord(channel_id)
        if not mapping or not mapping.xmpp:
            return

        discord_id = str(payload.user_id)
        nick = await self._identity.discord_to_xmpp(discord_id)
        if not nick:
            return

        from bridge.adapters.xmpp import XMPPAdapter

        xmpp_adapter = None
        for adapter in self._bus._adapters:  # type: ignore[attr-defined]
            if isinstance(adapter, XMPPAdapter):
                xmpp_adapter = adapter
                break

        if xmpp_adapter and xmpp_adapter._component:
            # Look up XMPP message ID from Discord message ID
            target_xmpp_id = xmpp_adapter._component._msgid_tracker.get_xmpp_id(str(payload.message_id))
            if target_xmpp_id:
                # Only send Unicode emoji, skip custom Discord emojis
                if payload.emoji.is_unicode_emoji():
                    emoji = str(payload.emoji)
                    await xmpp_adapter._component.send_reaction_as_user(
                        discord_id,
                        mapping.xmpp.muc_jid,
                        target_xmpp_id,
                        emoji,
                        nick,
                    )
                    logger.debug("Sent Discord reaction {} to XMPP", emoji)
                else:
                    logger.debug("Skipping custom Discord emoji: {}", payload.emoji.name)

    async def _on_reaction_remove(self, payload) -> None:
        """Handle Discord reaction remove; send empty reactions to XMPP."""
        # XEP-0444: Send empty reactions set to remove all reactions
        # For now, just log it
        logger.debug("Discord reaction removed: {} on {}", payload.emoji, payload.message_id)

    async def _on_message_delete(self, message: Message) -> None:
        """Handle Discord message delete; send retraction to XMPP."""
        if not self._identity:
            return

        channel_id = str(message.channel.id)
        mapping = self._router.get_mapping_for_discord(channel_id)
        if not mapping or not mapping.xmpp:
            return

        discord_id = str(message.author.id)
        nick = await self._identity.discord_to_xmpp(discord_id)
        if not nick:
            return

        from bridge.adapters.xmpp import XMPPAdapter

        xmpp_adapter = None
        for adapter in self._bus._adapters:  # type: ignore[attr-defined]
            if isinstance(adapter, XMPPAdapter):
                xmpp_adapter = adapter
                break

        if xmpp_adapter and xmpp_adapter._component:
            # Look up XMPP message ID from Discord message ID
            target_xmpp_id = xmpp_adapter._component._msgid_tracker.get_xmpp_id(str(message.id))
            if target_xmpp_id:
                await xmpp_adapter._component.send_retraction_as_user(
                    discord_id,
                    mapping.xmpp.muc_jid,
                    target_xmpp_id,
                    nick,
                )
                logger.debug("Sent Discord message deletion to XMPP")

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

        @bot.event
        async def on_message_edit(before: Message, after: Message) -> None:
            """Handle message edits."""
            await self._on_message_edit(before, after)

        @bot.event
        async def on_raw_reaction_add(payload) -> None:
            """Handle reaction adds."""
            await self._on_reaction_add(payload)

        @bot.event
        async def on_raw_reaction_remove(payload) -> None:
            """Handle reaction removes."""
            await self._on_reaction_remove(payload)

        @bot.event
        async def on_message_delete(message: Message) -> None:
            """Handle message deletes."""
            await self._on_message_delete(message)

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
