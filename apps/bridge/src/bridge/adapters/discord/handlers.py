"""Discord inbound event handlers: message, edit, reaction, typing, delete (AUDIT §2.B)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from discord import Message, MessageType, RawBulkMessageDeleteEvent, RawMessageDeleteEvent, TextChannel
from discord.enums import ReactionType
from loguru import logger

from bridge.events import message_delete, message_in

if TYPE_CHECKING:
    from bridge.adapters.discord.adapter import DiscordAdapter


def should_relay_message(message_type: MessageType) -> bool:
    """Return True if *message_type* should be relayed by the bridge.

    Only ``MessageType.default`` and ``MessageType.reply`` are relayed;
    all system/join/boost/etc. message types are filtered out.
    """
    return message_type in (MessageType.default, MessageType.reply)


def should_relay_reaction(reaction_type: ReactionType) -> bool:
    """Return True if *reaction_type* should be relayed by the bridge.

    Only ``ReactionType.normal`` reactions are relayed; burst (super)
    reactions are filtered out.
    """
    return reaction_type is ReactionType.normal


def is_bridge_echo(message: Message) -> bool:
    """Return True if *message* was sent by the bridge itself.

    Centralises the two checks that every inbound handler needs:
    1. ``webhook_id`` is set → the message came from a bridge webhook.
    2. ``author.bot`` is True → the message came from the bot user.
    """
    if getattr(message, "webhook_id", None):
        return True
    return bool(message.author.bot)


def is_own_reaction(adapter: DiscordAdapter, payload: object) -> bool:
    """Return True if the reaction *payload* was triggered by the bot itself."""
    user_id = getattr(payload, "user_id", None)
    if user_id is None:
        return False
    return bool(adapter._bot and adapter._bot.user and user_id == adapter._bot.user.id)


def _is_voice_message(message: Message) -> bool:
    """Return True if *message* is a Discord voice message (bit 13).

    Discord voice messages are audio recordings sent inline in chat.
    They have a special flag (bit 13 of message.flags) and carry the
    audio as an attachment. We relay the audio URL (preferring proxy_url
    for CDN reliability) rather than the message content.
    """
    flags = getattr(message, "flags", None)
    if flags is None:
        return False
    # discord.py ≥2.3 exposes .voice directly
    if hasattr(flags, "voice"):
        return bool(flags.voice)
    # Fallback: check bit 13 of the raw flags value
    return bool(getattr(flags, "value", 0) & (1 << 13))


async def on_message(adapter: DiscordAdapter, message: Message) -> None:
    """Handle incoming Discord message; emit MessageIn to bus."""
    if is_bridge_echo(message):
        return

    # Only relay default and reply messages; ignore system/join/boost/etc.
    if not should_relay_message(message.type):
        return

    channel_id = str(message.channel.id)
    if not adapter._is_bridged_channel(channel_id):
        return

    # Voice messages: relay the audio attachment URL or a placeholder.
    if _is_voice_message(message):
        avatar_url = str(message.author.display_avatar.url) if message.author.display_avatar else None
        voice_content = (
            (getattr(message.attachments[0], "proxy_url", None) or message.attachments[0].url)
            if message.attachments
            else "[voice message]"
        )
        _, evt = message_in(
            origin="discord",
            channel_id=channel_id,
            author_id=str(message.author.id),
            author_display=message.author.display_name or message.author.name,
            content=voice_content,
            message_id=str(message.id),
            is_action=False,
            avatar_url=avatar_url,
        )
        logger.info(
            "voice message bridged: channel={} author={}",
            channel_id,
            message.author.display_name or message.author.name,
        )
        adapter._bus.publish("discord", evt)
        return

    content = message.content or ""

    # Get avatar URL (needed for both attachments and content messages)
    avatar_url = str(message.author.display_avatar.url) if message.author.display_avatar else None

    # Handle attachments: emit each attachment's CDN URL as a message.
    if message.attachments:
        for attachment in message.attachments:
            att_raw: dict[str, object] = {}
            # Pass image/video dimensions for XEP-0446 file metadata
            if attachment.width and attachment.height:
                att_raw["media_width"] = attachment.width
                att_raw["media_height"] = attachment.height
            _, att_evt = message_in(
                origin="discord",
                channel_id=channel_id,
                author_id=str(message.author.id),
                author_display=message.author.display_name or message.author.name,
                content=getattr(attachment, "proxy_url", None) or attachment.url,
                message_id=f"{message.id}_attachment_{attachment.id}",
                is_action=False,
                avatar_url=avatar_url,
                raw=att_raw,
            )
            logger.info(
                "attachment bridged: channel={} author={} file={}",
                channel_id,
                message.author.display_name or message.author.name,
                attachment.filename,
            )
            adapter._bus.publish("discord", att_evt)
        if not content.strip():
            return

    if not content.strip():
        return

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
        elif adapter._bot:
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

    # Detect Discord /me action: message starting with "/me "
    is_action = False
    if content.startswith("/me "):
        is_action = True
        content = content[4:]  # strip "/me " prefix; relay will format for each target

    _, evt = message_in(
        origin="discord",
        channel_id=channel_id,
        author_id=str(message.author.id),
        author_display=message.author.display_name or message.author.name,
        content=content,
        message_id=str(message.id),
        reply_to_id=str(message.reference.message_id) if message.reference else None,
        is_edit=False,
        is_action=is_action,
        avatar_url=avatar_url,
        raw=raw,
    )
    logger.info(
        "message bridged: channel={} author={}",
        channel_id,
        message.author.display_name or message.author.name,
    )
    adapter._bus.publish("discord", evt)


async def on_raw_message_edit(adapter: DiscordAdapter, payload) -> None:
    """Handle Discord message edits via raw event (fires for cached and uncached messages)."""
    message = payload.message
    if is_bridge_echo(message):
        return

    channel_id = str(payload.channel_id)
    if not adapter._is_bridged_channel(channel_id):
        return

    content = message.content or ""
    if not content.strip() and adapter._bot:
        # Uncached: fetch message for content (MESSAGE_CONTENT intent may still not include it)
        try:
            channel = adapter._bot.get_channel(payload.channel_id)
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
    logger.debug("edit received: channel={} msg_id={}", channel_id, msg_id)
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
    adapter._bus.publish("discord", evt)


async def on_reaction_add(adapter: DiscordAdapter, payload) -> None:
    """Handle Discord reaction add; publish for Relay to route to IRC/XMPP."""
    if not payload.emoji.is_unicode_emoji():
        logger.debug("skipping custom emoji: {}", payload.emoji.name)
        return
    # Only relay normal reactions; filter out burst/super reactions.
    reaction_type = getattr(payload, "type", None)
    if reaction_type is not None and not should_relay_reaction(reaction_type):
        logger.debug("Skipping non-normal reaction type: {}", reaction_type)
        return
    # Skip our own reactions (from bridge relaying XMPP/IRC) to prevent echo
    if is_own_reaction(adapter, payload):
        return

    channel_id = str(payload.channel_id)
    mapping = adapter._router.get_mapping_for_discord(channel_id)
    if not mapping:
        return

    user = payload.member
    if not user and adapter._bot:
        user = await fetch_user(adapter, payload.user_id)
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
    logger.info("reaction bridged: channel={} author={} emoji={}", channel_id, author_display, str(payload.emoji))
    adapter._bus.publish("discord", evt)


async def fetch_user(adapter: DiscordAdapter, user_id: int):
    """Fetch user by ID if bot available."""
    if adapter._bot:
        try:
            return adapter._bot.get_user(user_id) or await adapter._bot.fetch_user(user_id)
        except Exception:
            pass
    return None


async def on_reaction_remove(adapter: DiscordAdapter, payload) -> None:
    """Handle Discord reaction remove; emit ReactionIn with is_remove=True for relay."""
    if not payload.emoji.is_unicode_emoji():
        return
    # Only relay normal reactions; filter out burst/super reactions.
    reaction_type = getattr(payload, "type", None)
    if reaction_type is not None and not should_relay_reaction(reaction_type):
        return
    # Skip our own reaction removals (from bridge relaying) to prevent echo
    if is_own_reaction(adapter, payload):
        return

    channel_id = str(payload.channel_id)
    mapping = adapter._router.get_mapping_for_discord(channel_id)
    if not mapping:
        return

    user = await fetch_user(adapter, payload.user_id)
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
        "reaction removal bridged: channel={} author={} emoji={}",
        channel_id,
        author_display,
        str(payload.emoji),
    )
    adapter._bus.publish("discord", evt)


async def on_typing(adapter: DiscordAdapter, channel, user) -> None:
    """Handle Discord typing; publish for Relay to route to IRC (throttled 3s)."""
    if user.bot:
        return
    channel_id = str(channel.id)
    if not adapter._is_bridged_channel(channel_id):
        return

    now = time.time()
    last = adapter._typing_publish_throttle.get(channel_id, 0)
    if now - last < 3:
        return
    adapter._typing_publish_throttle[channel_id] = now

    from bridge.events import typing_in

    _, evt = typing_in(origin="discord", channel_id=channel_id, user_id=str(user.id))
    adapter._bus.publish("discord", evt)


async def on_raw_message_delete(adapter: DiscordAdapter, payload: RawMessageDeleteEvent) -> None:
    """Handle Discord message deletes via raw event (fires for cached and uncached messages)."""
    channel_id = str(payload.channel_id)
    if not adapter._is_bridged_channel(channel_id):
        return

    # Skip when we initiated the delete (relaying from XMPP/IRC) — avoids duplicate retraction on XMPP
    key = f"{channel_id}:{payload.message_id}"
    if key in adapter._recently_deleted_by_us:
        logger.debug("skipping raw_message_delete for {} (we initiated)", payload.message_id)
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
    logger.info("message delete bridged: channel={} message_id={}", channel_id, payload.message_id)
    logger.debug(
        "publishing message_delete channel={} message_id={} -> relay (IRC needs msgid for REDACT)",
        channel_id,
        payload.message_id,
    )
    adapter._bus.publish("discord", evt)


async def on_raw_bulk_message_delete(adapter: DiscordAdapter, payload: RawBulkMessageDeleteEvent) -> None:
    """Handle Discord bulk message deletes (e.g. moderator purge)."""
    channel_id = str(payload.channel_id)
    if not adapter._is_bridged_channel(channel_id):
        return

    cached = {m.id: m for m in payload.cached_messages}
    logger.info("bulk delete bridged: channel={} count={}", channel_id, len(payload.message_ids))
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
        adapter._bus.publish("discord", evt)
