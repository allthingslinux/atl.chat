"""IRC outbound message sending — extracted from IRCClient.

All functions receive the client instance as the first parameter,
following the same pattern as the Discord and XMPP adapter outbound modules.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from loguru import logger

from bridge.adapters.irc.client import _nick_color
from bridge.config import cfg
from bridge.events import MessageOut
from bridge.formatting.irc_message_split import extract_code_blocks, split_irc_lines

if TYPE_CHECKING:
    from bridge.adapters.irc.client import IRCClient


def format_remote_nick(nick: str, protocol: str = "discord") -> str:
    """Format a remote nick using the configured remote_nick_format template.

    Supports ``{nick}`` and ``{protocol}`` variables.  Falls back to the
    default ``"<{nick}> "`` when the config value is missing or empty.

    Requirement 23.1, 23.2.
    """
    template = getattr(cfg, "remote_nick_format", None) or "<{nick}> "
    try:
        return template.format(nick=nick, protocol=protocol)
    except (KeyError, ValueError):
        return f"<{nick}> "


async def consume_outbound(client: IRCClient) -> None:
    """Consume outbound message queue with token bucket throttling."""
    while True:
        try:
            evt = await client._outbound.get()
            logger.debug("IRC: dequeued message discord_id={} channel={}", evt.message_id, evt.channel_id)
            # Wait for token before sending (flood control)
            wait = client._throttle.acquire()
            if wait > 0:
                logger.debug("IRC: throttle wait {:.2f}s for channel={}", wait, evt.channel_id)
                await asyncio.sleep(wait)
            client._throttle.use_token()  # Consume (guaranteed after acquire wait)
            await send_message(client, evt)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.exception("IRC send failed: {}", exc)


async def send_message(client: IRCClient, evt: MessageOut) -> None:
    """Send message to IRC. Uses RELAYMSG when available (stateless bridging)."""
    mapping = client._router.get_mapping_for_discord(evt.channel_id)
    if not mapping or not mapping.irc:
        logger.warning("IRC send skipped: no mapping for channel {}", evt.channel_id)
        return

    target = mapping.irc.channel
    content = evt.content
    logger.debug("IRC: send_message start target={} content={!r}", target, content[:80])

    # Add reply tag if replying and we have irc_msgid
    reply_tags = None
    if evt.reply_to_id:
        irc_msgid = client._msgid_tracker.get_irc_msgid(evt.reply_to_id)
        if irc_msgid:
            reply_tags = {"+draft/reply": irc_msgid}
            logger.debug("IRC: reply tag set for irc_msgid={}", irc_msgid)
        else:
            logger.debug("IRC: reply_to_id={} has no irc_msgid in tracker", evt.reply_to_id)
            # Do NOT strip > quote fallback: server denies +draft/reply (CLIENTTAGDENY),
            # so IRC clients ignore the tag. Keep the quote so users see reply context.

    # Extract fenced code blocks and upload them to a paste service
    processed = extract_code_blocks(content)
    if processed.blocks:
        logger.debug("IRC: found {} code block(s), uploading to paste", len(processed.blocks))
        from bridge.formatting.paste import upload_paste

        for i, block in enumerate(processed.blocks):
            url = await upload_paste(block.content, lang=block.lang)
            if url:
                label = url
                logger.debug("IRC: paste block {} uploaded -> {}", i, url)
            else:
                # Upload failed — inline a truncated snippet so nothing is silently lost
                snippet = block.content.replace("\n", " ").strip()[:80]
                label = f"[code] (paste failed) {snippet}…"
                logger.warning("IRC: paste block {} upload failed, using inline snippet", i)
            processed.text = processed.text.replace(f"{{PASTE_{i}}}", label)
        content = processed.text
        logger.info("IRC: paste replaced content -> {!r}", content[:120])
    else:
        content = processed.text

    # IRC forbids \r, \0 in message payload; newlines are split into separate messages
    content = content.replace("\r", "").replace("\x00", "")

    chunks = split_irc_lines(content, max_bytes=450)
    logger.debug("IRC: split into {} chunk(s) for {}", len(chunks), target)

    # Spoofed nick for RELAYMSG: display/discord (Valware requires '/' in nick)
    display = str(evt.author_display or evt.author_id or "user").strip()
    spoofed_nick = client._sanitize_relaymsg_nick(display)

    use_relaymsg = client._has_relaymsg()
    is_action = getattr(evt, "is_action", False)
    logger.debug("IRC: use_relaymsg={} spoofed_nick={} is_action={}", use_relaymsg, spoofed_nick, is_action)

    for i, chunk in enumerate(chunks):
        logger.debug("IRC: sending chunk {}/{} to {} -> {!r}", i + 1, len(chunks), target, chunk[:80])
        if is_action:
            # CTCP ACTION (/me): wrap in \x01ACTION ...\x01
            # RELAYMSG doesn't support CTCP, fall back to PRIVMSG with colored prefix
            action_text = f"\x01ACTION {chunk}\x01"
            colored_prefix = f"{_nick_color(display)} "
            prefixed = colored_prefix + action_text if i == 0 else action_text
            tags = reply_tags if i == 0 else None
            if tags:
                await client.rawmsg("PRIVMSG", target, prefixed, tags=tags)
            else:
                await client.message(target, prefixed)
            if i == 0:
                logger.info("IRC: sent CTCP ACTION to {} as {}", target, spoofed_nick)
        elif use_relaymsg:
            # RELAYMSG #channel spoofed_nick :message
            if reply_tags and i == 0:
                await client.rawmsg("RELAYMSG", target, spoofed_nick, chunk, tags=reply_tags)
            else:
                await client.rawmsg("RELAYMSG", target, spoofed_nick, chunk)
            if i == 0:
                logger.info("IRC: sent RELAYMSG to {} as {}", target, spoofed_nick)
                client._recent_relaymsg_sends[(client._server, target, spoofed_nick)] = None
        else:
            # PRIVMSG fallback: prefix message with configurable remote nick format
            colored_prefix = f"{_nick_color(display)} "
            prefixed = colored_prefix + chunk if i == 0 else chunk
            tags = reply_tags if i == 0 else None
            if tags:
                await client.rawmsg("PRIVMSG", target, prefixed, tags=tags)
            else:
                await client.message(target, prefixed)
            if i == 0:
                logger.info("IRC: sent PRIVMSG to {} as {}", target, spoofed_nick)
        # Only store mapping for first chunk (echo will have msgid)
        if i == 0:
            client._pending_sends.put_nowait(evt.message_id)
            logger.debug(
                "IRC: queued pending_send discord_id={} for echo correlation",
                evt.message_id,
            )
