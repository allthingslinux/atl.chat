"""Discord webhook utilities: get/create, send, edit, reply button (AUDIT §2.B)."""

from __future__ import annotations

from discord import AllowedMentions, ButtonStyle, TextChannel
from discord.ext import commands
from discord.ui import Button, View
from discord.webhook import Webhook
from loguru import logger

# Webhook username: 2-32 chars (AUDIT §3)
MIN_USERNAME_LEN = 2
MAX_USERNAME_LEN = 32
WEBHOOK_NAME = "ATL Bridge"
DISCORD_WEBHOOKS_PER_CHANNEL = 10
REPLY_BUTTON_MAX_LABEL = 77
_ALLOWED_MENTIONS = AllowedMentions(everyone=False, roles=False)
_AVATAR_INTERNAL_HOSTS = ("atl-xmpp-server", "localhost", "127.0.0.1")


def _ensure_valid_username(name: str) -> str:
    """Truncate or pad username to fit Discord webhook limits."""
    name = str(name)[:MAX_USERNAME_LEN]
    if len(name) < MIN_USERNAME_LEN:
        name = name + "_" * (MIN_USERNAME_LEN - len(name))
    return name


def _avatar_url_ok_for_discord(url: str | None) -> bool:
    """True if avatar URL is publicly fetchable by Discord (not internal)."""
    if not url:
        return False
    return not any(h in url.lower() for h in _AVATAR_INTERNAL_HOSTS)


def _reply_button_view(author: str, content: str | None, url: str) -> View:
    """Build Unifier/lightning style link button: ↪️ Author · content (truncated)."""
    content_clean = (content or "").replace("\n", " ").strip()
    label = f"{author} · {content_clean}" if content_clean else author
    if len(label) > REPLY_BUTTON_MAX_LABEL:
        label = label[: REPLY_BUTTON_MAX_LABEL - 3] + "..."
    view = View()
    view.add_item(Button(style=ButtonStyle.link, label=f"↪️ {label}", url=url))
    return view


async def get_or_create_webhook(
    bot: commands.Bot,
    channel_id: str,
    webhook_cache: dict,
) -> Webhook | None:
    """Get or create one webhook per channel (matterbridge pattern). Caller must hold send lock."""
    channel = bot.get_channel(int(channel_id))
    if not channel or not isinstance(channel, TextChannel):
        logger.warning("Discord channel {} not found or not a text channel", channel_id)
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
) -> int | None:
    """Send message via webhook. Optional Unifier/lightning style link button for replies."""
    send_avatar_url = avatar_url if _avatar_url_ok_for_discord(avatar_url) else None
    send_kw: dict = {
        "content": content[:2000],
        "username": _ensure_valid_username(author_display),
        "avatar_url": send_avatar_url,
        "allowed_mentions": _ALLOWED_MENTIONS,
        "wait": True,
    }
    if reply_to_id and bot:
        channel = bot.get_channel(int(channel_id))
        if channel and isinstance(channel, TextChannel) and channel.guild:
            jump_url = f"https://discord.com/channels/{channel.guild.id}/{channel_id}/{reply_to_id}"
            author = reply_author or "Unknown"
            send_kw["view"] = _reply_button_view(author, reply_content, jump_url)
    msg = await webhook.send(**send_kw)
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
        logger.debug("Could not edit Discord message {}: {}", discord_message_id, exc)
        return False
