"""Discord outbound handlers: delete, reaction, typing, attachments (AUDIT §2.B)."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

import aiohttp
from discord import Message, TextChannel
from discord.ext import commands
from loguru import logger

from bridge.events import MessageDeleteOut, ReactionOut, TypingOut, message_in

if TYPE_CHECKING:
    from bridge.gateway import Bus, ChannelRouter
    from bridge.gateway.msgid_resolver import MessageIDResolver
    from bridge.identity import IdentityResolver


async def handle_delete_out(bot: commands.Bot | None, evt: MessageDeleteOut) -> None:
    """Delete Discord message when IRC REDACT or XMPP retraction received."""
    if not bot:
        return
    channel = bot.get_channel(int(evt.channel_id))
    if not channel or not isinstance(channel, TextChannel):
        return
    try:
        msg = await channel.fetch_message(int(evt.message_id))
        await msg.delete()
        logger.info("Discord: deleted message {} (from IRC REDACT / XMPP retraction)", evt.message_id)
    except Exception as exc:
        logger.debug("Could not delete Discord message {}: {}", evt.message_id, exc)


async def handle_reaction_out(bot: commands.Bot | None, evt: ReactionOut) -> None:
    """Add or remove reaction on Discord message when IRC/XMPP reaction received."""
    if not bot:
        return
    channel = bot.get_channel(int(evt.channel_id))
    if not channel or not isinstance(channel, TextChannel):
        return
    is_remove = evt.raw.get("is_remove", False)
    try:
        msg = await channel.fetch_message(int(evt.message_id))
        if is_remove:
            await msg.remove_reaction(evt.emoji, bot.user)
            logger.info("Discord: removed reaction {} from message {} (from IRC/XMPP)", evt.emoji, evt.message_id)
        else:
            await msg.add_reaction(evt.emoji)
            logger.info("Discord: added reaction {} to message {} (from IRC/XMPP)", evt.emoji, evt.message_id)
    except Exception as exc:
        logger.debug(
            "Could not {} reaction on {}: {}",
            "remove" if is_remove else "add",
            evt.message_id,
            exc,
        )


async def handle_typing_out(
    bot: commands.Bot | None,
    evt: TypingOut,
    typing_throttle: dict[str, float],
) -> None:
    """Trigger Discord typing indicator when IRC typing received (throttled 3s)."""
    if not bot:
        return

    now = time.time()
    last = typing_throttle.get(evt.channel_id, 0)
    if now - last < 3:
        return
    typing_throttle[evt.channel_id] = now

    channel = bot.get_channel(int(evt.channel_id))
    if not channel or not isinstance(channel, TextChannel):
        return
    try:
        async with channel.typing():
            await asyncio.sleep(5)
    except Exception as exc:
        logger.debug("Could not trigger typing for {}: {}", evt.channel_id, exc)


async def handle_attachments(
    message: Message,
    *,
    identity: IdentityResolver | None,
    router: ChannelRouter,
    msgid_resolver: MessageIDResolver | None,
    bus: Bus,
    session: aiohttp.ClientSession | None,
) -> None:
    """Download Discord attachments and send via XMPP HTTP upload or IRC URL notification."""
    if not identity:
        return

    channel_id = str(message.channel.id)
    mapping = router.get_mapping_for_discord(channel_id)
    if not mapping:
        return

    discord_id = str(message.author.id)

    # Send to XMPP via HTTP upload if configured
    if mapping.xmpp and msgid_resolver:
        nick = await identity.discord_to_xmpp(discord_id)
        # DevIdentityResolver returns None; use display name as fallback for dev without Portal
        if not nick:
            nick = (message.author.display_name or message.author.name or "user")[:20]
        if nick:
            xmpp_component = msgid_resolver.get_xmpp_component()

            if xmpp_component:
                for attachment in message.attachments:
                    if attachment.size > 10 * 1024 * 1024:
                        continue

                    try:
                        if session:
                            async with session.get(attachment.url) as resp:
                                if resp.status == 200:
                                    data = await resp.read()
                                    await xmpp_component.send_file_with_fallback(
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
            bus.publish("discord", evt)
