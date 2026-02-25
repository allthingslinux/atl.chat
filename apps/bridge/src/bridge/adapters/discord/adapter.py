"""Discord adapter: bot, webhooks per identity, queue for outbound (AUDIT §2)."""

from __future__ import annotations

import asyncio
import contextlib
import io
import os
import time
from typing import TYPE_CHECKING

import aiohttp
from cachetools import TTLCache
from discord import File, Intents, Message, RawBulkMessageDeleteEvent, RawMessageDeleteEvent, TextChannel
from discord.ext import commands
from discord.webhook import Webhook
from loguru import logger

from bridge.adapters.base import AdapterBase
from bridge.adapters.discord import handlers as discord_handlers
from bridge.adapters.discord import webhook as discord_webhook
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
    from bridge.gateway.msgid_resolver import MessageIDResolver
    from bridge.identity import IdentityResolver


class DiscordAdapter(AdapterBase):
    """Discord adapter: receives messages, sends via webhooks with queue."""

    def __init__(
        self,
        bus: Bus,
        router: ChannelRouter,
        identity_resolver: IdentityResolver | None,
        msgid_resolver: MessageIDResolver | None = None,
    ) -> None:
        self._bus = bus
        self._router = router
        self._identity = identity_resolver
        self._msgid_resolver = msgid_resolver
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
        if not self._bot:
            return None
        return await discord_webhook.get_or_create_webhook(self._bot, channel_id, self._webhook_cache)

    async def _webhook_send(
        self,
        channel_id: str,
        author_display: str,
        content: str,
        *,
        avatar_url: str | None = None,
        reply_to_id: str | None = None,
        reply_author: str | None = None,
        reply_content: str | None = None,
    ) -> int | None:
        """Send message via webhook. Optional Unifier/lightning style link button for replies."""
        webhook = await self._get_or_create_webhook(channel_id)
        if not webhook:
            return None
        return await discord_webhook.webhook_send(
            webhook,
            channel_id,
            self._bot,
            author_display,
            content,
            avatar_url=avatar_url,
            reply_to_id=reply_to_id,
            reply_author=reply_author,
            reply_content=reply_content,
        )

    async def _fetch_reply_context(self, channel_id: str, reply_to_id: str) -> tuple[str, str | None]:
        """Fetch original message author and content for reply button. Returns (author, content)."""
        if not self._bot:
            return ("Unknown", None)
        channel = self._bot.get_channel(int(channel_id))
        if not channel or not isinstance(channel, TextChannel):
            return ("Unknown", None)
        try:
            ref_msg = await channel.fetch_message(int(reply_to_id))
            author = ref_msg.author.display_name or getattr(ref_msg.author, "name", "Unknown")
            content = ref_msg.content or None
            return (author, content)
        except Exception as exc:
            logger.debug("Could not fetch reply context for {}: {}", reply_to_id, exc)
            return ("Unknown", None)

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
        return await discord_webhook.webhook_edit(webhook, discord_message_id, content)

    def _resolve_discord_message_id(self, replace_id: str, origin: str) -> str | None:
        """Resolve source protocol message ID to Discord message ID via MessageIDResolver."""
        if self._msgid_resolver:
            return self._msgid_resolver.get_discord_id(origin, replace_id)
        return None

    async def _handle_delete_out(self, evt: MessageDeleteOut) -> None:
        """Delete Discord message when IRC REDACT or XMPP retraction received."""
        await discord_handlers.handle_delete_out(self._bot, evt)

    async def _handle_reaction_out(self, evt: ReactionOut) -> None:
        """Add or remove reaction on Discord message when IRC/XMPP reaction received."""
        await discord_handlers.handle_reaction_out(self._bot, evt)

    async def _handle_typing_out(self, evt: TypingOut) -> None:
        """Trigger Discord typing indicator when IRC typing received (throttled 3s)."""
        await discord_handlers.handle_typing_out(self._bot, evt, self._typing_throttle)

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
                    content = evt.content  # Relay already strips reply fallback for discord target
                    # Resolve reply_to_id: XMPP tracker may have IRC msgid when original was from IRC
                    reply_to_discord_id = evt.reply_to_id
                    if reply_to_discord_id and not reply_to_discord_id.isdigit():
                        resolved = self._resolve_discord_message_id(reply_to_discord_id, "irc")
                        if resolved:
                            reply_to_discord_id = resolved
                    reply_author: str | None = None
                    reply_content: str | None = None
                    if reply_to_discord_id:
                        reply_author, reply_content = await self._fetch_reply_context(
                            evt.channel_id, reply_to_discord_id
                        )
                    async with self._send_lock:
                        discord_msg_id = await self._webhook_send(
                            evt.channel_id,
                            evt.author_display,
                            content,
                            avatar_url=evt.avatar_url,
                            reply_to_id=reply_to_discord_id,
                            reply_author=reply_author,
                            reply_content=reply_content,
                        )
                # Store XMPP->Discord mapping for retraction, reaction, and edit routing
                origin = (evt.raw or {}).get("origin")
                if discord_msg_id and origin == "xmpp" and self._msgid_resolver:
                    mapping = self._router.get_mapping_for_discord(evt.channel_id)
                    if mapping and mapping.xmpp:
                        self._msgid_resolver.store_xmpp(
                            evt.message_id,
                            str(discord_msg_id),
                            mapping.xmpp.muc_jid,
                        )
                        for alias in (evt.raw or {}).get("xmpp_id_aliases", []):
                            if alias and alias != evt.message_id:
                                self._msgid_resolver.add_xmpp_alias(alias, evt.message_id)
                        logger.debug(
                            "Stored XMPP->Discord mapping: xmpp_id={} -> discord_id={} (for reactions/edits)",
                            evt.message_id,
                            discord_msg_id,
                        )
                # Store IRC->Discord mapping for REDACT routing
                if discord_msg_id and evt.raw.get("origin") == "irc" and self._msgid_resolver:
                    self._msgid_resolver.store_irc(evt.message_id, str(discord_msg_id))
                    # Link discord_id -> xmpp_id so Discord replies to IRC webhooks resolve for XMPP
                    irc_msgid = evt.message_id
                    if self._msgid_resolver.add_discord_id_alias(str(discord_msg_id), irc_msgid):
                        logger.debug(
                            "Linked Discord reply target: discord_id={} -> xmpp (via irc_msgid={})",
                            discord_msg_id,
                            irc_msgid,
                        )
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("Webhook send failed: {}", exc)

    def _is_bridged_channel(self, channel_id: str) -> bool:
        return self._router.get_mapping_for_discord(str(channel_id)) is not None

    async def _handle_attachments(self, message: Message) -> None:
        """Download Discord attachments and send via XMPP HTTP upload or IRC URL notification."""
        await discord_handlers.handle_attachments(
            message,
            identity=self._identity,
            router=self._router,
            msgid_resolver=self._msgid_resolver,
            bus=self._bus,
            session=self._session,
        )

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
        avatar_url = str(message.author.display_avatar.url) if message.author.display_avatar else None

        # For replies: include referenced message content + author so relay can add quote for IRC
        raw: dict[str, object] = {}
        if message.reference:
            ref_content: str | None = None
            ref_author: str | None = None
            resolved = getattr(message.reference, "resolved", None)
            if resolved is not None:
                ref_content = getattr(resolved, "content", None) or ""
                ref_author = (
                    getattr(resolved.author, "display_name", None)
                    or getattr(resolved.author, "name", None)
                    or str(getattr(resolved.author, "id", ""))
                )
            elif self._bot:
                try:
                    ref_msg = await message.channel.fetch_message(message.reference.message_id)
                    ref_content = ref_msg.content or ""
                    ref_author = (
                        getattr(ref_msg.author, "display_name", None)
                        or getattr(ref_msg.author, "name", None)
                        or str(getattr(ref_msg.author, "id", ""))
                    )
                except Exception:
                    pass
            if ref_content:
                raw["reply_quoted_content"] = ref_content
            if ref_author:
                raw["reply_quoted_author"] = ref_author

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
            raw=raw,
        )
        logger.info(
            "Discord message bridged: channel={} author={}",
            channel_id,
            message.author.display_name or message.author.name,
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

        avatar_url = str(message.author.display_avatar.url) if message.author.display_avatar else None

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
        if self._bot and self._bot.user and payload.user_id == self._bot.user.id:
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
        logger.info(
            "Discord reaction bridged: channel={} author={} emoji={}", channel_id, author_display, str(payload.emoji)
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
        if self._bot and self._bot.user and payload.user_id == self._bot.user.id:
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
        logger.info(
            "Discord reaction removal bridged: channel={} author={} emoji={}",
            channel_id,
            author_display,
            str(payload.emoji),
        )
        self._bus.publish("discord", evt)

    async def _on_typing(self, channel, user) -> None:
        """Handle Discord typing; publish for Relay to route to IRC (throttled 3s)."""
        if user.bot:
            return
        channel_id = str(channel.id)
        if not self._is_bridged_channel(channel_id):
            return

        now = time.time()
        last = self._typing_publish_throttle.get(channel_id, 0)
        if now - last < 3:
            return
        self._typing_publish_throttle[channel_id] = now

        from bridge.events import typing_in

        _, evt = typing_in(origin="discord", channel_id=channel_id, user_id=str(user.id))
        self._bus.publish("discord", evt)

    async def _on_raw_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        """Handle Discord message deletes via raw event (fires for cached and uncached messages)."""
        channel_id = str(payload.channel_id)
        if not self._is_bridged_channel(channel_id):
            return

        author_id = ""
        author_display = ""
        if payload.cached_message:
            author_id = str(payload.cached_message.author.id)
            author_display = (
                getattr(
                    payload.cached_message.author,
                    "global_name",
                    None,
                )
                or getattr(payload.cached_message.author, "name", "")
                or ""
            )

        _, evt = message_delete(
            origin="discord",
            channel_id=channel_id,
            message_id=str(payload.message_id),
            author_id=author_id,
            author_display=author_display,
        )
        logger.info("Discord message delete bridged: channel={} message_id={}", channel_id, payload.message_id)
        logger.debug(
            "Discord: publishing message_delete channel={} message_id={} -> relay (IRC needs msgid for REDACT)",
            channel_id,
            payload.message_id,
        )
        self._bus.publish("discord", evt)

    async def _on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent) -> None:
        """Handle Discord bulk message deletes (e.g. moderator purge)."""
        channel_id = str(payload.channel_id)
        if not self._is_bridged_channel(channel_id):
            return

        cached = {m.id: m for m in payload.cached_messages}
        logger.info("Discord bulk delete bridged: channel={} count={}", channel_id, len(payload.message_ids))
        for message_id in payload.message_ids:
            author_id = ""
            author_display = ""
            if message_id in cached:
                a = cached[message_id].author
                author_id = str(a.id)
                author_display = getattr(a, "global_name", None) or getattr(a, "name", "") or ""
            _, evt = message_delete(
                origin="discord",
                channel_id=channel_id,
                message_id=str(message_id),
                author_id=author_id,
                author_display=author_display,
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
        intents.messages = True  # Required for on_raw_message_delete / on_raw_bulk_message_delete
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
