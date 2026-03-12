"""Discord adapter: bot, webhooks per identity, queue for outbound (AUDIT §2)."""

from __future__ import annotations

import asyncio
import contextlib
import os
from typing import TYPE_CHECKING

import aiohttp
from cachetools import TTLCache
from discord import Intents, Message, RawBulkMessageDeleteEvent, RawMessageDeleteEvent, TextChannel
from discord.ext import commands
from discord.webhook import Webhook
from loguru import logger

from bridge.adapters.base import AdapterBase
from bridge.adapters.discord import avatar as discord_avatar
from bridge.adapters.discord import handlers as discord_handlers
from bridge.adapters.discord import media as discord_media
from bridge.adapters.discord import outbound as discord_outbound
from bridge.adapters.discord import webhook as discord_webhook
from bridge.events import (
    MessageDeleteOut,
    MessageOut,
    ReactionOut,
    TypingOut,
)
from bridge.formatting.mention_resolution import resolve_mentions
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
        # Message IDs we deleted (relaying from XMPP/IRC) — skip publishing on_raw_message_delete
        self._recently_deleted_by_us: TTLCache[str, None] = TTLCache(maxsize=500, ttl=5)
        self._channel_locks: dict[str, asyncio.Lock] = {}
        self._bot: commands.Bot | None = None
        self._session: aiohttp.ClientSession | None = None
        self._consumer_task: asyncio.Task | None = None
        self._bot_task: asyncio.Task | None = None
        self._typing_throttle: dict[str, float] = {}  # channel_id -> last_sent
        self._typing_publish_throttle: dict[str, float] = {}  # channel_id -> last_published

    @property
    def name(self) -> str:
        return "discord"

    # ------------------------------------------------------------------
    # Event routing
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_channel_lock(self, channel_id: str) -> asyncio.Lock:
        """Get or create a per-channel send lock."""
        if channel_id not in self._channel_locks:
            self._channel_locks[channel_id] = asyncio.Lock()
        return self._channel_locks[channel_id]

    def _is_bridged_channel(self, channel_id: str) -> bool:
        return self._router.get_mapping_for_discord(str(channel_id)) is not None

    # ------------------------------------------------------------------
    # Outbound delegation (thin wrappers for backward compat)
    # ------------------------------------------------------------------

    async def _handle_delete_out(self, evt: MessageDeleteOut) -> None:
        await discord_outbound.handle_delete_out(self._bot, evt, self._recently_deleted_by_us)

    async def _handle_reaction_out(self, evt: ReactionOut) -> None:
        await discord_outbound.handle_reaction_out(self._bot, evt)

    async def _handle_typing_out(self, evt: TypingOut) -> None:
        await discord_outbound.handle_typing_out(self._bot, evt, self._typing_throttle)

    # ------------------------------------------------------------------
    # Inbound delegation (thin wrappers for backward compat)
    # ------------------------------------------------------------------

    async def _on_message(self, message: Message) -> None:
        await discord_handlers.on_message(self, message)

    async def _on_raw_message_edit(self, payload) -> None:
        await discord_handlers.on_raw_message_edit(self, payload)

    async def _on_reaction_add(self, payload) -> None:
        await discord_handlers.on_reaction_add(self, payload)

    async def _on_reaction_remove(self, payload) -> None:
        await discord_handlers.on_reaction_remove(self, payload)

    async def _on_typing(self, channel, user) -> None:
        await discord_handlers.on_typing(self, channel, user)

    async def _on_raw_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        await discord_handlers.on_raw_message_delete(self, payload)

    async def _on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent) -> None:
        await discord_handlers.on_raw_bulk_message_delete(self, payload)

    # ------------------------------------------------------------------
    # Media delegation
    # ------------------------------------------------------------------

    async def _prepare_media(self, content: str):
        return await discord_media.prepare_media(self._session, content)

    async def _handle_attachments(self, message: Message) -> None:
        await discord_outbound.handle_attachments(
            message,
            identity=self._identity,
            router=self._router,
            msgid_resolver=self._msgid_resolver,
            bus=self._bus,
            session=self._session,
        )

    async def upload_file(self, channel_id: str, data: bytes, filename: str) -> None:
        await discord_media.upload_file(self._bot, channel_id, data, filename)

    # ------------------------------------------------------------------
    # Avatar delegation
    # ------------------------------------------------------------------

    def _resolve_xmpp_avatar_fallback(self, evt: MessageOut) -> str | None:
        return discord_avatar.resolve_xmpp_avatar_fallback(evt, self._router)

    async def _resolve_avatar_for_send(self, evt: MessageOut) -> str | None:
        """Resolve avatar URL: prefer Portal, then evt.avatar_url, then XMPP fallback."""
        if self._identity and evt.author_id:
            origin = (evt.raw or {}).get("origin", "")
            try:
                if origin == "discord":
                    url = await self._identity.avatar_for_discord(evt.author_id)
                elif origin == "irc":
                    url = await self._identity.avatar_for_irc(evt.author_id)
                elif origin == "xmpp":
                    real_jid = (evt.raw or {}).get("real_jid")
                    url = await self._identity.avatar_for_xmpp(real_jid if isinstance(real_jid, str) else evt.author_id)
                else:
                    url = await self._identity.avatar_for_discord(evt.author_id)
                if url:
                    return url
            except Exception as exc:
                logger.debug("Portal avatar lookup failed for {}: {}", evt.author_id, exc)
        return evt.avatar_url or self._resolve_xmpp_avatar_fallback(evt)

    # ------------------------------------------------------------------
    # Webhook delegation
    # ------------------------------------------------------------------

    async def _get_or_create_webhook(self, channel_id: str) -> Webhook | None:
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
        file=None,
    ) -> int | None:
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
            file=file,
        )

    async def _webhook_edit(self, channel_id: str, discord_message_id: int, content: str) -> bool:
        webhook = await self._get_or_create_webhook(channel_id)
        if not webhook:
            return False
        return await discord_webhook.webhook_edit(webhook, discord_message_id, content)

    def _resolve_discord_message_id(self, replace_id: str, origin: str) -> str | None:
        if self._msgid_resolver:
            return self._msgid_resolver.get_discord_id(origin, replace_id)
        return None

    async def _fetch_reply_context(self, channel_id: str, reply_to_id: str) -> tuple[str, str | None]:
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

    async def _fetch_user(self, user_id: int):
        return await discord_handlers.fetch_user(self, user_id)

    # ------------------------------------------------------------------
    # Queue consumer
    # ------------------------------------------------------------------

    async def _queue_consumer(self, delay: float = 0.25) -> None:
        """Background consumer: pop from queue, send via webhook with delay (AUDIT §3)."""
        while True:
            try:
                evt = await self._queue.get()
                logger.debug(
                    "dequeued MessageOut discord_id={} channel={} author={}",
                    evt.message_id,
                    evt.channel_id,
                    evt.author_display,
                )

                is_edit = evt.raw.get("is_edit", False)
                replace_id = evt.raw.get("replace_id")
                origin = evt.raw.get("origin", "")

                discord_msg_id: int | None = None
                if is_edit and replace_id and self._bot:
                    resolved = self._resolve_discord_message_id(replace_id, origin)
                    logger.debug(
                        "edit resolve replace_id={} origin={} -> discord_id={}",
                        replace_id,
                        origin,
                        resolved,
                    )
                    if resolved:
                        edit_content = evt.content
                        if edit_content:
                            channel = self._bot.get_channel(int(evt.channel_id))
                            guild = getattr(channel, "guild", None) if channel else None
                            if guild:
                                edit_content = resolve_mentions(edit_content, guild)
                        async with self._get_channel_lock(evt.channel_id):
                            edited = await self._webhook_edit(evt.channel_id, int(resolved), edit_content)
                        if edited:
                            discord_msg_id = int(resolved)
                            logger.info("edited message {} via webhook (replace_id={})", resolved, replace_id)
                        else:
                            logger.warning("webhook edit failed for message {}", resolved)

                # Send as new message if not edited
                if discord_msg_id is None:
                    content = evt.content
                    logger.debug(
                        "sending new message channel={} author={} content={!r}",
                        evt.channel_id,
                        evt.author_display,
                        content[:80],
                    )
                    if self._bot and content:
                        channel = self._bot.get_channel(int(evt.channel_id))
                        guild = getattr(channel, "guild", None) if channel else None
                        if guild:
                            content = resolve_mentions(content, guild)
                    content, file_obj, temp_path = await self._prepare_media(content)
                    reply_to_discord_id = evt.reply_to_id
                    if reply_to_discord_id and not reply_to_discord_id.isdigit():
                        resolved = self._resolve_discord_message_id(reply_to_discord_id, "irc")
                        if resolved:
                            reply_to_discord_id = resolved
                    reply_author: str | None = None
                    reply_content: str | None = None
                    if reply_to_discord_id:
                        reply_author, reply_content = await self._fetch_reply_context(
                            evt.channel_id,
                            reply_to_discord_id,
                        )
                    async with self._get_channel_lock(evt.channel_id):
                        avatar_url = await self._resolve_avatar_for_send(evt)
                        discord_msg_id = await self._webhook_send(
                            evt.channel_id,
                            evt.author_display,
                            content,
                            avatar_url=avatar_url,
                            reply_to_id=reply_to_discord_id,
                            reply_author=reply_author,
                            reply_content=reply_content,
                            file=file_obj,
                        )
                    if discord_msg_id:
                        logger.info(
                            "sent webhook message {} channel={} author={}",
                            discord_msg_id,
                            evt.channel_id,
                            evt.author_display,
                        )
                    else:
                        logger.warning(
                            "webhook send returned no message id channel={} author={}",
                            evt.channel_id,
                            evt.author_display,
                        )
                    if temp_path and os.path.exists(temp_path):
                        with contextlib.suppress(OSError):
                            os.unlink(temp_path)

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
                    # Link Discord ID to IRC msgid so IRC reactions work (IRC echo stored xmpp_id)
                    if self._msgid_resolver.add_irc_discord_id_alias(str(discord_msg_id), evt.message_id):
                        logger.debug(
                            "Linked Discord ID to IRC tracker: discord_id={} -> xmpp_id={} (IRC reactions now work)",
                            discord_msg_id,
                            evt.message_id,
                        )
                # Store IRC->Discord mapping for REDACT routing
                if discord_msg_id and evt.raw.get("origin") == "irc" and self._msgid_resolver:
                    self._msgid_resolver.store_irc(evt.message_id, str(discord_msg_id))
                    irc_msgid = evt.message_id
                    if self._msgid_resolver.resolve_irc_xmpp_pending(irc_msgid, str(discord_msg_id)):
                        logger.debug(
                            "Resolved IRC→XMPP pending: irc_msgid={} -> discord_id={} (XMPP reactions now work)",
                            irc_msgid,
                            discord_msg_id,
                        )
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

    # ------------------------------------------------------------------
    # Bridge status command
    # ------------------------------------------------------------------

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
        parts.append(f"IRC: {irc_nick}" if irc_nick else "IRC: not linked")
        parts.append(f"XMPP: {xmpp_jid}" if xmpp_jid else "XMPP: not linked")
        await ctx.reply(" | ".join(parts))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start Discord bot and queue consumer."""
        token = os.environ.get("BRIDGE_DISCORD_TOKEN")
        if not token:
            logger.warning("BRIDGE_DISCORD_TOKEN not set; adapter disabled")
            return

        intents = Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True
        intents.members = True
        intents.typing = True

        bot = commands.Bot(command_prefix="!", intents=intents)

        @bot.event
        async def on_ready() -> None:
            logger.info("bot ready: {}", bot.user)

        @bot.event
        async def on_message(message: Message) -> None:
            if message.content and message.content.strip().startswith("!bridge"):
                await bot.process_commands(message)
                return
            await self._on_message(message)

        @bot.event
        async def on_raw_message_edit(payload) -> None:
            await self._on_raw_message_edit(payload)

        @bot.event
        async def on_raw_reaction_add(payload) -> None:
            await self._on_reaction_add(payload)

        @bot.event
        async def on_raw_reaction_remove(payload) -> None:
            await self._on_reaction_remove(payload)

        @bot.event
        async def on_raw_message_delete(payload) -> None:
            await self._on_raw_message_delete(payload)

        @bot.event
        async def on_raw_bulk_message_delete(payload) -> None:
            await self._on_raw_bulk_message_delete(payload)

        @bot.event
        async def on_typing(channel, user, when) -> None:
            await self._on_typing(channel, user)

        @bot.command(name="bridge")
        async def cmd_bridge(ctx: commands.Context, *args: str) -> None:
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
        self._channel_locks.clear()
