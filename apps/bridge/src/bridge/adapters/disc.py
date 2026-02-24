"""Discord adapter: bot, webhooks per identity, queue for outbound (AUDIT §2)."""

from __future__ import annotations

import asyncio
import contextlib
import io
import os
from typing import TYPE_CHECKING

import aiohttp
from cachetools import TTLCache
from discord import AllowedMentions, File, Intents, Message, TextChannel
from discord.ext import commands
from discord.webhook import Webhook
from loguru import logger

from bridge.events import (
    MessageDeleteOut,
    MessageOut,
    ReactionOut,
    TypingOut,
    message_delete,
    message_in,
)
from bridge.gateway import Bus, ChannelRouter

if TYPE_CHECKING:
    from bridge.identity import IdentityResolver

# Webhook username: 2-32 chars (AUDIT §3)
MIN_USERNAME_LEN = 2
MAX_USERNAME_LEN = 32

# One webhook per channel (matterbridge pattern); username/avatar per message
WEBHOOK_NAME = "ATL Bridge"
DISCORD_WEBHOOKS_PER_CHANNEL = 10


def _ensure_valid_username(name: str) -> str:
    """Truncate or pad username to fit Discord webhook limits."""
    name = str(name)[:MAX_USERNAME_LEN]
    if len(name) < MIN_USERNAME_LEN:
        name = name + "_" * (MIN_USERNAME_LEN - len(name))
    return name


# Disable mass pings for bridged content; user mentions are allowed (IRC/XMPP don't produce snowflake syntax).
_ALLOWED_MENTIONS = AllowedMentions(everyone=False, roles=False)


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
        self._webhook_cache: TTLCache[str, Webhook] = TTLCache(maxsize=100, ttl=86400)
        self._send_lock = asyncio.Lock()
        self._bot: commands.Bot | None = None
        self._session: aiohttp.ClientSession | None = None
        self._consumer_task: asyncio.Task | None = None
        self._bot_task: asyncio.Task | None = None
        self._typing_throttle: dict[str, float] = {}  # channel_id -> last_sent
        self._typing_publish_throttle: dict[str, float] = {}  # channel_id -> last_published

    @property
    def name(self) -> str:
        return "discord"

    def accept_event(self, source: str, evt: object) -> bool:
        """Accept MessageOut, MessageDeleteOut, ReactionOut, or TypingOut targeting Discord."""
        if isinstance(evt, MessageOut) and evt.target_origin == "discord":
            return True
        if isinstance(evt, MessageDeleteOut) and evt.target_origin == "discord":
            return True
        return (isinstance(evt, ReactionOut) and evt.target_origin == "discord") or (
            isinstance(evt, TypingOut) and evt.target_origin == "discord"
        )

    def push_event(self, source: str, evt: object) -> None:
        """Queue MessageOut for webhook send, or handle MessageDeleteOut/ReactionOut/TypingOut."""
        if isinstance(evt, MessageDeleteOut) and evt.target_origin == "discord":
            asyncio.create_task(self._handle_delete_out(evt))  # noqa: RUF006
            return
        if isinstance(evt, ReactionOut) and evt.target_origin == "discord":
            asyncio.create_task(self._handle_reaction_out(evt))  # noqa: RUF006
            return
        if isinstance(evt, TypingOut) and evt.target_origin == "discord":
            asyncio.create_task(self._handle_typing_out(evt))  # noqa: RUF006
            return
        if isinstance(evt, MessageOut):
            self._queue.put_nowait(evt)

    async def _get_or_create_webhook(self, channel_id: str) -> Webhook | None:
        """Get or create one webhook per channel (matterbridge pattern). Caller must hold _send_lock."""
        bot = self._bot
        if not bot:
            return None

        channel = bot.get_channel(int(channel_id))
        if not channel or not isinstance(channel, TextChannel):
            logger.warning("Discord channel {} not found or not a text channel", channel_id)
            return None

        webhook = self._webhook_cache.get(channel_id)

        if not webhook:
            try:
                webhooks = await channel.webhooks()
                app_id = str(bot.application_id) if getattr(bot, "application_id", None) else None

                # 1) Reuse existing webhook with our name (from previous runs)
                for wh in webhooks:
                    if wh.name == WEBHOOK_NAME:
                        webhook = wh
                        logger.debug("Reusing webhook '{}' for channel {}", wh.name, channel_id)
                        break

                # 2) Fallback: use any webhook owned by our app when at limit
                if not webhook and app_id and len(webhooks) >= DISCORD_WEBHOOKS_PER_CHANNEL:
                    for wh in webhooks:
                        if str(getattr(wh, "application_id", None) or "") == app_id:
                            webhook = wh
                            logger.info(
                                "Reusing app-owned webhook '{}' for channel {} (limit reached)",
                                wh.name,
                                channel_id,
                            )
                            break

                # 3) Create only if no reusable webhook found
                if not webhook and len(webhooks) < DISCORD_WEBHOOKS_PER_CHANNEL:
                    webhook = await channel.create_webhook(
                        name=WEBHOOK_NAME,
                        reason="ATL Bridge relay",
                    )
                if webhook:
                    self._webhook_cache[channel_id] = webhook
            except Exception as exc:
                logger.exception("Failed to get/create webhook for channel {}: {}", channel_id, exc)
                return None

        if not webhook:
            logger.warning(
                "No webhook available for channel {}: Discord allows {} webhooks/channel. "
                "Remove unused webhooks in Server Settings → Integrations, or use one owned by this bot.",
                channel_id,
                DISCORD_WEBHOOKS_PER_CHANNEL,
            )
            return None

        return webhook

    async def _webhook_send(
        self,
        channel_id: str,
        author_display: str,
        content: str,
        *,
        avatar_url: str | None = None,
    ) -> int | None:
        """Send message via webhook. One webhook per channel; username/avatar per message."""
        webhook = await self._get_or_create_webhook(channel_id)
        if not webhook:
            return None

        msg = await webhook.send(
            content=content[:2000],
            username=_ensure_valid_username(author_display),
            avatar_url=avatar_url,
            allowed_mentions=_ALLOWED_MENTIONS,
            wait=True,
        )
        return int(msg.id) if msg else None

    async def _webhook_edit(
        self,
        channel_id: str,
        discord_message_id: int,
        content: str,
    ) -> bool:
        """Edit webhook message by ID. Same webhook that created it can edit it."""
        webhook = await self._get_or_create_webhook(channel_id)
        if not webhook:
            return False

        try:
            await webhook.edit_message(
                discord_message_id,
                content=content[:2000],
                allowed_mentions=_ALLOWED_MENTIONS,
            )
            return True
        except Exception as exc:
            logger.debug(
                "Could not edit Discord message {} (replace_id lookup may be stale): {}",
                discord_message_id,
                exc,
            )
            return False

    def _resolve_discord_message_id(self, replace_id: str, origin: str) -> str | None:
        """Resolve source protocol message ID to Discord message ID via trackers."""
        if origin == "xmpp":
            from bridge.adapters.xmpp import XMPPAdapter

            for adapter in self._bus._adapters:
                if isinstance(adapter, XMPPAdapter) and adapter._component:
                    return adapter._component._msgid_tracker.get_discord_id(replace_id)
        elif origin == "irc":
            from bridge.adapters.irc import IRCAdapter

            for adapter in self._bus._adapters:
                if isinstance(adapter, IRCAdapter) and adapter._msgid_tracker:
                    return adapter._msgid_tracker.get_discord_id(replace_id)
        return None

    async def _handle_delete_out(self, evt: MessageDeleteOut) -> None:
        """Delete Discord message when IRC REDACT or XMPP retraction received."""
        if not self._bot:
            return
        channel = self._bot.get_channel(int(evt.channel_id))
        if not channel or not isinstance(channel, TextChannel):
            return
        try:
            msg = await channel.fetch_message(int(evt.message_id))
            await msg.delete()
            logger.debug("Deleted Discord message {} from IRC/XMPP", evt.message_id)
        except Exception as exc:
            logger.debug("Could not delete Discord message {}: {}", evt.message_id, exc)

    async def _handle_reaction_out(self, evt: ReactionOut) -> None:
        """Add or remove reaction on Discord message when IRC/XMPP reaction received."""
        if not self._bot:
            return
        channel = self._bot.get_channel(int(evt.channel_id))
        if not channel or not isinstance(channel, TextChannel):
            return
        is_remove = evt.raw.get("is_remove", False)
        try:
            msg = await channel.fetch_message(int(evt.message_id))
            if is_remove:
                await msg.remove_reaction(evt.emoji, self._bot.user)
                logger.debug(
                    "Removed reaction {} from Discord message {}", evt.emoji, evt.message_id
                )
            else:
                await msg.add_reaction(evt.emoji)
                logger.debug("Added reaction {} to Discord message {}", evt.emoji, evt.message_id)
        except Exception as exc:
            logger.debug(
                "Could not {} reaction on {}: {}",
                "remove" if is_remove else "add",
                evt.message_id,
                exc,
            )

    async def _handle_typing_out(self, evt: TypingOut) -> None:
        """Trigger Discord typing indicator when IRC typing received (throttled 3s)."""
        if not self._bot:
            return
        import time

        now = time.time()
        last = self._typing_throttle.get(evt.channel_id, 0)
        if now - last < 3:
            return
        self._typing_throttle[evt.channel_id] = now

        channel = self._bot.get_channel(int(evt.channel_id))
        if not channel or not isinstance(channel, TextChannel):
            return
        try:
            async with channel.typing():
                await asyncio.sleep(5)
        except Exception as exc:
            logger.debug("Could not trigger typing for {}: {}", evt.channel_id, exc)

    async def _queue_consumer(self, delay: float = 0.25) -> None:
        """Background consumer: pop from queue, send via webhook with delay (AUDIT §3)."""
        while True:
            try:
                evt = await self._queue.get()

                # Check if this is an edit (XMPP correction or IRC edit)
                is_edit = evt.raw.get("is_edit", False)
                replace_id = evt.raw.get("replace_id")
                origin = evt.raw.get("origin", "")

                discord_msg_id: int | None = None
                if is_edit and replace_id and self._bot:
                    resolved = self._resolve_discord_message_id(replace_id, origin)
                    if resolved:
                        async with self._send_lock:
                            edited = await self._webhook_edit(
                                evt.channel_id,
                                int(resolved),
                                evt.content,
                            )
                        if edited:
                            discord_msg_id = int(resolved)
                            logger.debug(
                                "Edited Discord message {} (replace_id: {})",
                                resolved,
                                replace_id,
                            )

                # Send as new message if not edited
                if discord_msg_id is None:
                    async with self._send_lock:
                        discord_msg_id = await self._webhook_send(
                            evt.channel_id,
                            evt.author_display,
                            evt.content,
                            avatar_url=evt.raw.get("avatar_url"),
                        )
                # Store XMPP->Discord mapping for retraction, reaction, and edit routing
                origin = (evt.raw or {}).get("origin")
                if discord_msg_id and origin == "xmpp":
                    mapping = self._router.get_mapping_for_discord(evt.channel_id)
                    if mapping and mapping.xmpp:
                        from bridge.adapters.xmpp import XMPPAdapter

                        stored = False
                        for adapter in self._bus._adapters:
                            if isinstance(adapter, XMPPAdapter) and adapter._component:
                                tracker = adapter._component._msgid_tracker
                                tracker.store(
                                    evt.message_id,
                                    str(discord_msg_id),
                                    mapping.xmpp.muc_jid,
                                )
                                for alias in (evt.raw or {}).get("xmpp_id_aliases", []):
                                    if alias and alias != evt.message_id:
                                        tracker.add_alias(alias, evt.message_id)
                                stored = True
                                logger.debug(
                                    "Stored XMPP->Discord mapping: xmpp_id={} -> discord_id={} (for reactions/edits)",
                                    evt.message_id,
                                    discord_msg_id,
                                )
                                break
                        if not stored:
                            logger.warning(
                                "XMPP->Discord: no XMPP adapter with component; reaction lookup will fail for msg {}",
                                discord_msg_id,
                            )
                # Store IRC->Discord mapping for REDACT routing
                if discord_msg_id and evt.raw.get("origin") == "irc":
                    from bridge.adapters.irc import IRCAdapter

                    for adapter in self._bus._adapters:
                        if isinstance(adapter, IRCAdapter) and adapter._msgid_tracker:
                            adapter._msgid_tracker.store(evt.message_id, str(discord_msg_id))
                            break
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
                            if self._session:
                                async with self._session.get(attachment.url) as resp:
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
        # Skip webhook-originated messages first (our own bridge output) — most definitive
        if getattr(message, "webhook_id", None):
            return
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
        avatar_url = (
            str(message.author.display_avatar.url) if message.author.display_avatar else None
        )

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

    async def _on_raw_message_edit(self, payload) -> None:
        """Handle Discord message edits via raw event (fires for cached and uncached messages)."""
        message = payload.message
        if message.author.bot:
            return
        if getattr(message, "webhook_id", None):
            return

        channel_id = str(payload.channel_id)
        if not self._is_bridged_channel(channel_id):
            return

        content = message.content or ""
        if not content.strip() and self._bot:
            # Uncached: fetch message for content (MESSAGE_CONTENT intent may still not include it)
            try:
                channel = self._bot.get_channel(payload.channel_id)
                if isinstance(channel, TextChannel):
                    fetched = await channel.fetch_message(payload.message_id)
                    content = fetched.content or ""
                    message = fetched
            except Exception:
                pass
        if not content.strip():
            return

        avatar_url = (
            str(message.author.display_avatar.url) if message.author.display_avatar else None
        )

        msg_id = str(getattr(message, "id", None) or payload.message_id)
        logger.debug("Discord edit received: channel={} msg_id={}", channel_id, msg_id)
        _, evt = message_in(
            origin="discord",
            channel_id=channel_id,
            author_id=str(message.author.id),
            author_display=message.author.display_name or message.author.name,
            content=content,
            message_id=msg_id,
            reply_to_id=str(message.reference.message_id) if message.reference else None,
            is_edit=True,
            is_action=False,
            avatar_url=avatar_url,
            raw={"replace_id": msg_id},
        )
        self._bus.publish("discord", evt)

    async def _on_reaction_add(self, payload) -> None:
        """Handle Discord reaction add; publish for Relay to route to IRC/XMPP."""
        if not payload.emoji.is_unicode_emoji():
            logger.debug("Skipping custom Discord emoji: {}", payload.emoji.name)
            return
        # Skip our own reactions (from bridge relaying XMPP/IRC) to prevent echo
        if self._bot and payload.user_id == self._bot.user.id:
            return

        channel_id = str(payload.channel_id)
        mapping = self._router.get_mapping_for_discord(channel_id)
        if not mapping:
            return

        user = payload.member
        if not user and self._bot:
            user = await self._fetch_user(payload.user_id)
        author_display = user.display_name if user else str(payload.user_id)

        from bridge.events import reaction_in

        _, evt = reaction_in(
            origin="discord",
            channel_id=channel_id,
            message_id=str(payload.message_id),
            emoji=str(payload.emoji),
            author_id=str(payload.user_id),
            author_display=author_display,
        )
        self._bus.publish("discord", evt)

    async def _fetch_user(self, user_id: int):
        """Fetch user by ID if bot available."""
        if self._bot:
            try:
                return self._bot.get_user(user_id) or await self._bot.fetch_user(user_id)
            except Exception:
                pass
        return None

    async def _on_reaction_remove(self, payload) -> None:
        """Handle Discord reaction remove; emit ReactionIn with is_remove=True for relay."""
        if not payload.emoji.is_unicode_emoji():
            return
        # Skip our own reaction removals (from bridge relaying) to prevent echo
        if self._bot and payload.user_id == self._bot.user.id:
            return

        channel_id = str(payload.channel_id)
        mapping = self._router.get_mapping_for_discord(channel_id)
        if not mapping:
            return

        user = await self._fetch_user(payload.user_id)
        author_display = user.display_name if user else str(payload.user_id)

        from bridge.events import reaction_in

        _, evt = reaction_in(
            origin="discord",
            channel_id=channel_id,
            message_id=str(payload.message_id),
            emoji=str(payload.emoji),
            author_id=str(payload.user_id),
            author_display=author_display,
            raw={"is_remove": True},
        )
        self._bus.publish("discord", evt)

    async def _on_typing(self, channel, user) -> None:
        """Handle Discord typing; publish for Relay to route to IRC (throttled 3s)."""
        if user.bot:
            return
        channel_id = str(channel.id)
        if not self._is_bridged_channel(channel_id):
            return
        import time

        now = time.time()
        last = self._typing_publish_throttle.get(channel_id, 0)
        if now - last < 3:
            return
        self._typing_publish_throttle[channel_id] = now

        from bridge.events import typing_in

        _, evt = typing_in(origin="discord", channel_id=channel_id, user_id=str(user.id))
        self._bus.publish("discord", evt)

    async def _on_raw_message_delete(self, payload) -> None:
        """Handle Discord message deletes via raw event (fires for cached and uncached messages)."""
        channel_id = str(payload.channel_id)
        if not self._is_bridged_channel(channel_id):
            return

        author_id = ""
        if payload.cached_message:
            author_id = str(payload.cached_message.author.id)

        _, evt = message_delete(
            origin="discord",
            channel_id=channel_id,
            message_id=str(payload.message_id),
            author_id=author_id,
        )
        self._bus.publish("discord", evt)

    async def _on_raw_bulk_message_delete(self, payload) -> None:
        """Handle Discord bulk message deletes (e.g. moderator purge)."""
        channel_id = str(payload.channel_id)
        if not self._is_bridged_channel(channel_id):
            return

        cached = {m.id: m for m in payload.cached_messages}
        for message_id in payload.message_ids:
            author_id = str(cached[message_id].author.id) if message_id in cached else ""
            _, evt = message_delete(
                origin="discord",
                channel_id=channel_id,
                message_id=str(message_id),
                author_id=author_id,
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
        token = os.environ.get("BRIDGE_DISCORD_TOKEN")
        if not token:
            logger.warning("BRIDGE_DISCORD_TOKEN not set; Discord adapter disabled")
            return

        intents = Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        intents.typing = True

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
        async def on_raw_message_edit(payload) -> None:
            """Handle message edits (raw: fires for cached and uncached messages)."""
            await self._on_raw_message_edit(payload)

        @bot.event
        async def on_raw_reaction_add(payload) -> None:
            """Handle reaction adds."""
            await self._on_reaction_add(payload)

        @bot.event
        async def on_raw_reaction_remove(payload) -> None:
            """Handle reaction removes."""
            await self._on_reaction_remove(payload)

        @bot.event
        async def on_raw_message_delete(payload) -> None:
            """Handle message deletes (raw: fires for cached and uncached messages)."""
            await self._on_raw_message_delete(payload)

        @bot.event
        async def on_raw_bulk_message_delete(payload) -> None:
            """Handle bulk message deletes (e.g. moderator purge)."""
            await self._on_raw_bulk_message_delete(payload)

        @bot.event
        async def on_typing(channel, user, when) -> None:
            """Handle typing; publish for Relay to route to IRC."""
            await self._on_typing(channel, user)

        @bot.command(name="bridge")
        async def cmd_bridge(ctx: commands.Context, *args: str) -> None:
            """!bridge or !bridge status: show linked IRC/XMPP accounts."""
            await self._cmd_bridge_status(ctx)

        self._bot = bot
        self._session = aiohttp.ClientSession()
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
        if self._session:
            await self._session.close()
        self._bot = None
        self._session = None
        self._bot_task = None
