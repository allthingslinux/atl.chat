"""Discord webhook utilities: get/create, send, edit, reply subtext (OOYE-style)."""

from __future__ import annotations

import asyncio

import discord
from discord import AllowedMentions, File, TextChannel
from discord.ext import commands
from discord.webhook import Webhook
from loguru import logger

from bridge.adapters.discord.reply_emoji import get_reply_prefix

# Webhook username: 2-32 chars (AUDIT §3)
MIN_USERNAME_LEN = 2
MAX_USERNAME_LEN = 32
WEBHOOK_NAME = "ATL Bridge"
DISCORD_WEBHOOKS_PER_CHANNEL = 10
REPLY_CONTENT_MAX = 50
_ALLOWED_MENTIONS = AllowedMentions(everyone=False, roles=False)
_AVATAR_INTERNAL_HOSTS = ("atl-xmpp-server", "localhost", "127.0.0.1")


def _ensure_valid_username(name: str) -> str:
    """Truncate or pad username to fit Discord webhook limits."""
    name = str(name)[:MAX_USERNAME_LEN]
    if len(name) < MIN_USERNAME_LEN:
        name = name + "_" * (MIN_USERNAME_LEN - len(name))
    return name


def _avatar_url_ok_for_discord(url: str | None) -> bool:
    """True if avatar URL is publicly fetchable by Discord (not internal or data:)."""
    if not url:
        return False
    if url.strip().lower().startswith("data:"):
        return False  # Discord cannot fetch data: URLs
    return not any(h in url.lower() for h in _AVATAR_INTERNAL_HOSTS)


def _build_reply_line(
    reply_to_id: str,
    channel_id: str,
    guild_id: str | None,
    author: str | None,
    content: str | None,
) -> str:
    """Build an OOYE-style reply subtext line prepended above the message.

    Produces:  -# > <:L1:id><:L2:id> https://discord.com/channels/.../... **Author**: preview...
    Falls back to ↪ if the application emojis haven't been uploaded yet.
    Uses Discord's -# (subtext) syntax so it renders subtle, like native replies.
    """
    prefix = get_reply_prefix()
    if guild_id:
        jump_url = f"https://discord.com/channels/{guild_id}/{channel_id}/{reply_to_id}"
        link_part = f"{prefix} {jump_url}"
    else:
        link_part = prefix

    author_part = f"**{author}**" if author else ""

    if not content:
        content_part = ""
    else:
        content_clean = content.replace("\n", " ").strip()
        if content_clean:
            preview = content_clean[:REPLY_CONTENT_MAX]
            suffix = "..." if len(content_clean) > REPLY_CONTENT_MAX else ""
            content_part = f": {preview}{suffix}"
        else:
            content_part = ""

    inner = " ".join(p for p in [link_part, author_part] if p) + content_part
    return f"-# > {inner}\n"


async def get_or_create_webhook(
    bot: commands.Bot,
    channel_id: str,
    webhook_cache: dict,
    webhook_create_locks: dict[str, asyncio.Lock] | None = None,
) -> Webhook | None:
    """Get or create one webhook per channel (matterbridge pattern).

    Webhooks allow the bridge to send messages that appear to come from
    different users (with custom username and avatar), rather than all
    messages appearing from the bot account. We reuse a single webhook
    per channel (named "ATL Bridge") to stay within Discord's 10-webhook
    limit per channel.

    A per-channel lock (webhook_create_locks) serializes the cache-check +
    webhook-create operation so that two concurrent callers cannot both see
    a cache miss and both independently create a new webhook for the same channel.
    """
    # Acquire (or create) a per-channel lock to prevent concurrent cache-miss
    # races where multiple tasks each see an empty cache entry and each try to
    # create a new webhook for the same channel.
    if webhook_create_locks is not None:
        if channel_id not in webhook_create_locks:
            webhook_create_locks[channel_id] = asyncio.Lock()
        lock: asyncio.Lock | None = webhook_create_locks[channel_id]
    else:
        lock = None

    async def _do_get_or_create() -> Webhook | None:
        channel = bot.get_channel(int(channel_id))
        if not channel:
            # get_channel uses cache; cache can be empty on connect/reconnect. Fallback to API.
            try:
                channel = await bot.fetch_channel(int(channel_id))
            except Exception as exc:
                logger.warning("channel {} not found (get_channel and fetch_channel): {}", channel_id, exc)
                return None
        if not channel or not isinstance(channel, TextChannel):
            logger.warning("channel {} not found or not a text channel", channel_id)
            return None

        webhook = webhook_cache.get(channel_id)
        if not webhook:
            try:
                webhooks = await channel.webhooks()
                app_id = str(getattr(bot, "application_id", None) or "")
                for wh in webhooks:
                    if wh.name == WEBHOOK_NAME:
                        webhook = wh
                        logger.debug("Reusing webhook '{}' for channel {}", wh.name, channel_id)
                        break
                if not webhook and app_id and len(webhooks) >= DISCORD_WEBHOOKS_PER_CHANNEL:
                    for wh in webhooks:
                        if str(getattr(wh, "application_id", None) or "") == app_id:
                            webhook = wh
                            logger.info("Reusing app-owned webhook for channel {} (limit reached)", channel_id)
                            break
                if not webhook and len(webhooks) < DISCORD_WEBHOOKS_PER_CHANNEL:
                    webhook = await channel.create_webhook(name=WEBHOOK_NAME, reason="ATL Bridge relay")
                if webhook:
                    webhook_cache[channel_id] = webhook
            except Exception as exc:
                logger.exception("Failed to get/create webhook for channel {}: {}", channel_id, exc)
                return None
        if not webhook:
            logger.warning(
                "No webhook available for channel {}: Discord allows {} webhooks/channel.",
                channel_id,
                DISCORD_WEBHOOKS_PER_CHANNEL,
            )
        return webhook

    if lock is not None:
        async with lock:
            return await _do_get_or_create()
    return await _do_get_or_create()


async def webhook_send(
    webhook: Webhook,
    channel_id: str,
    bot: commands.Bot | None,
    author_display: str,
    content: str,
    *,
    avatar_url: str | None = None,
    reply_to_id: str | None = None,
    reply_author: str | None = None,
    reply_content: str | None = None,
    file: File | None = None,
    webhook_cache: dict | None = None,
) -> int | None:
    """Send message via webhook with optional file attachment.

    When reply_to_id is set, prepends an OOYE-style -# > subtext line above
    the message instead of a button, matching Discord's native reply appearance.

    If the webhook returns 404 (stale/deleted), the cache entry for channel_id
    is evicted so the next send will create a fresh webhook.
    """
    send_avatar_url = avatar_url if _avatar_url_ok_for_discord(avatar_url) else None

    if reply_to_id:
        guild_id: str | None = None
        if bot:
            channel = bot.get_channel(int(channel_id))
            if channel and isinstance(channel, TextChannel) and channel.guild:
                guild_id = str(channel.guild.id)
        reply_line = _build_reply_line(reply_to_id, channel_id, guild_id, reply_author, reply_content)
        content = reply_line + (content or "")

    send_kw: dict = {
        "content": content[:2000] if content else None,
        "username": _ensure_valid_username(author_display),
        "avatar_url": send_avatar_url,
        "allowed_mentions": _ALLOWED_MENTIONS,
        "wait": True,
    }
    if file is not None:
        send_kw["file"] = file
    try:
        msg = await webhook.send(**send_kw)
    except discord.NotFound:
        # Stale or deleted webhook — evict from cache so the next send recreates it.
        if webhook_cache is not None and channel_id in webhook_cache:
            del webhook_cache[channel_id]
            logger.warning(
                "Webhook for channel {} returned 404 (deleted/stale); evicted from cache",
                channel_id,
            )
        raise
    return int(msg.id) if msg else None


async def webhook_edit(
    webhook: Webhook,
    discord_message_id: int,
    content: str,
) -> bool:
    """Edit webhook message by ID."""
    try:
        await webhook.edit_message(
            discord_message_id,
            content=content[:2000],
            allowed_mentions=_ALLOWED_MENTIONS,
        )
        return True
    except Exception as exc:
        logger.debug("could not edit message {}: {}", discord_message_id, exc)
        return False
