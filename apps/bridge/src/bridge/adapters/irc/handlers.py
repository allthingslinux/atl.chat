"""IRC inbound event handlers — extracted from IRCClient.

All functions receive the client instance as the first parameter,
following the same pattern as the Discord and XMPP adapter handlers.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from loguru import logger

from bridge.events import message_in

if TYPE_CHECKING:
    from bridge.adapters.irc.client import IRCClient


# ---------------------------------------------------------------------------
# Echo suppression utilities (Requirement 17.1)
# ---------------------------------------------------------------------------


def _is_relayed_by_us(client: IRCClient, tags: dict) -> bool:
    """Return True if the message was relayed by us via RELAYMSG (draft/relaymsg tag)."""
    return tags.get("draft/relaymsg") == client.nickname or tags.get("relaymsg") == client.nickname


def is_own_echo(client: IRCClient, source: str, tags: dict) -> bool:
    """Return True if *source* is the bridge's own nick or the message was relayed by us.

    Checks:
    1. source matches the client's own nickname (echo-message from server)
    2. draft/relaymsg tag matches our nick (RELAYMSG echo)
    """
    if source == client.nickname:
        return True
    return _is_relayed_by_us(client, tags)


def is_puppet_echo(client: IRCClient, source: str) -> bool:
    """Return True if *source* is one of our puppet nicks.

    The main connection receives PRIVMSGs from puppets; these must be
    suppressed to prevent double-relay.
    """
    if client._puppet_nick_check is not None:
        return client._puppet_nick_check(source)
    return False


def is_relaymsg_echo(client: IRCClient, server: str, target: str, source: str, tags: dict) -> bool:
    """Return True if the message matches a recent RELAYMSG send (TTLCache fallback).

    When the relaymsg tag is missing (e.g. via irc-services or UnrealIRCd
    quirks), we fall back to checking the recent-sends cache.
    """
    return (server, target, source) in client._recent_relaymsg_sends


# ---------------------------------------------------------------------------
# Charset handling (Requirement 16.2)
# ---------------------------------------------------------------------------


def decode_irc_bytes(data: bytes) -> str:
    """Decode IRC bytes: try UTF-8 first, fall back to ISO-8859-1.

    Note: pydle already handles this internally via ``FALLBACK_ENCODING``.
    This utility documents the requirement and provides an explicit function
    for any raw byte handling outside pydle's pipeline.
    """
    try:
        return data.decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        return data.decode("iso-8859-1")


# ---------------------------------------------------------------------------
# History replay suppression (Requirement 18.2)
# ---------------------------------------------------------------------------

# Maximum age (seconds) for a server-time timestamp to be considered current.
# IRC servers with +H (history replay) send old messages on join with a
# ``time`` tag in ISO 8601 format. 30 seconds is generous enough to handle
# clock skew and network latency while still filtering out genuine replays
# (which are typically minutes to hours old).
_HISTORY_REPLAY_THRESHOLD_SECONDS = 30


def is_history_replay(tags: dict) -> bool:
    """Return True if the message has a server-time timestamp >30s in the past.

    IRC servers with +H (history replay) send old messages on join with a
    ``time`` tag in ISO 8601 format.  We discard these to avoid re-relaying
    stale content.
    """
    time_str = tags.get("time")
    if not time_str:
        return False
    try:
        msg_time = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        now = datetime.now(UTC)
        age = (now - msg_time).total_seconds()
        return age > _HISTORY_REPLAY_THRESHOLD_SECONDS
    except (ValueError, TypeError):
        return False


async def handle_message(client: IRCClient, target: str, source: str, message: str) -> None:
    """Handle channel message; emit MessageIn to bus."""
    if not client._ready:
        return
    if not target.startswith("#"):
        return

    mapping = client._router.get_mapping_for_irc(client._server, target)
    if not mapping:
        return

    # Extract msgid and reply from IRCv3 tags
    msgid = None
    reply_to = None
    tags = {}
    if hasattr(client, "_message_tags") and client._message_tags:
        tags = client._message_tags
        msgid = tags.get("msgid")
        reply_to = tags.get("+draft/reply")

    # History replay suppression (Requirement 18.2): discard messages with
    # server-time timestamps significantly in the past (>30s).
    # Exception: messages in a chathistory batch are intentionally replayed
    # and should NOT be suppressed.
    in_chathistory = tags.get("batch") in client._chathistory_batches if tags.get("batch") else False
    if not in_chathistory and is_history_replay(tags):
        logger.debug("IRC: discarding history replay message from {} in {}", source, target)
        return

    message_id = msgid or f"irc:{client._server}:{target}:{source}:{id(message)}"

    # Resolve reply_to to Discord message ID if available
    discord_reply_to = None
    if reply_to:
        discord_reply_to = client._msgid_tracker.get_discord_id(reply_to)

    # Echo suppression: check all echo conditions via centralized utilities.
    # Three layers of echo detection prevent double-relay:
    # 1. is_own_echo: source matches our nick OR draft/relaymsg tag matches us
    # 2. is_puppet_echo: source is one of our puppet connections
    # 3. is_relaymsg_echo: TTLCache fallback when relaymsg tag is missing
    if (
        is_own_echo(client, source, tags)
        or is_puppet_echo(client, source)
        or is_relaymsg_echo(client, client._server, target, source, tags)
    ):
        # labeled-response correlation (Req 11.5): use label tag for reliable echo matching
        label = tags.get("label")
        if label and label in client._pending_labels:
            discord_id = client._pending_labels.pop(label)
            if msgid:
                client._msgid_tracker.store(msgid, discord_id)
                logger.debug("IRC: label={} correlated msgid {} -> {} for REDACT/edit", label, msgid, discord_id)
            else:
                logger.debug("IRC: label={} matched but no msgid tag on echo", label)
        elif msgid:
            try:
                discord_id = client._pending_sends.get_nowait()
                client._msgid_tracker.store(msgid, discord_id)  # irc_msgid, discord_id
                logger.debug("IRC: stored msgid {} -> {} for REDACT/edit correlation", msgid, discord_id)
            except asyncio.QueueEmpty:
                logger.debug(
                    "IRC: RELAYMSG echo had msgid {} but no pending_send (queue empty); cannot correlate",
                    msgid,
                )
        elif is_relaymsg_echo(client, client._server, target, source, tags) or _is_relayed_by_us(client, tags):
            logger.info(
                "IRC: RELAYMSG echo received for {} in {} but no msgid tag (UnrealIRCd message-ids may not add msgid to relaymsg)",
                source,
                target,
            )
            logger.debug(
                "IRC: RELAYMSG echo tags={} (empty => server may not send tags or message-tags cap not negotiated)",
                tags,
            )
        return  # Skip publishing our own echoed messages to prevent doubling

    if msgid:
        logger.debug("IRC: external message with msgid={} from {}", msgid, source)

    _, evt = message_in(
        origin="irc",
        channel_id=mapping.discord_channel_id,
        author_id=source,
        author_display=source,
        content=message,
        message_id=message_id,
        reply_to_id=discord_reply_to,
        is_action=False,
        raw={"tags": tags, "irc_msgid": msgid, "irc_reply_to": reply_to},
    )
    logger.info("IRC message bridged: channel={} author={}", target, source)
    client._bus.publish("irc", evt)

    # Track last message timestamp for CHATHISTORY AFTER on reconnect
    time_str = tags.get("time")
    if time_str:
        client._last_message_times[target] = time_str


async def handle_ctcp_action(client: IRCClient, by: str, target: str, message: str) -> None:
    """Handle /me action; emit MessageIn with action flag."""
    if not client._ready:
        return
    if not target.startswith("#"):
        return

    mapping = client._router.get_mapping_for_irc(client._server, target)
    if not mapping:
        return

    # Echo suppression: skip our own, puppet, and relaymsg echoes (same as handle_message)
    tags = getattr(client, "_message_tags", {}) or {}
    if (
        is_own_echo(client, by, tags)
        or is_puppet_echo(client, by)
        or is_relaymsg_echo(client, client._server, target, by, tags)
    ):
        return

    content = f"* {by} {message}"
    _, evt = message_in(
        origin="irc",
        channel_id=mapping.discord_channel_id,
        author_id=by,
        author_display=by,
        content=content,
        message_id=f"irc:{client._server}:{target}:{by}:{id(message)}",
        is_action=True,
    )
    logger.info("IRC action bridged: channel={} author={}", target, by)
    client._bus.publish("irc", evt)


async def handle_ctcp_version(client: IRCClient, by: str, target: str, contents: str) -> None:
    """Respond to CTCP VERSION queries with bridge info."""
    await client.ctcp_reply(by, "VERSION", "ATL Bridge (Discord\u2194IRC\u2194XMPP) https://atl.chat")


async def handle_ctcp_source(client: IRCClient, by: str, target: str, contents: str) -> None:
    """Respond to CTCP SOURCE queries with the project URL."""
    await client.ctcp_reply(by, "SOURCE", "https://github.com/allthingslinux/atl.chat")


async def handle_tagmsg(client: IRCClient, message: object) -> None:
    """Handle IRC TAGMSG with +draft/react, +draft/unreact, or +typing; publish for Relay."""
    if not client._ready:
        return
    params = getattr(message, "params", [])
    if not params:
        return
    target = params[0]
    if not target.startswith("#"):
        return
    mapping = client._router.get_mapping_for_irc(client._server, target)
    if not mapping:
        return

    tags = getattr(message, "tags", {}) or {}
    reply_to = tags.get("+draft/reply")
    react = tags.get("+draft/react")
    unreact = tags.get("+draft/unreact")
    typing_val = tags.get("typing")

    source = getattr(message, "source", "") or ""
    nick = source.split("!")[0] if "!" in source else source

    if react and reply_to:
        # Add reaction
        if nick == client.nickname:
            return  # Skip our own echo
        discord_id = client._msgid_tracker.get_discord_id(reply_to)
        if discord_id:
            from bridge.events import reaction_in

            msgid = tags.get("msgid")
            if msgid:
                client._reaction_tracker.store_incoming(msgid, discord_id, react, nick)
            _, evt = reaction_in(
                origin="irc",
                channel_id=f"{client._server}/{target}",
                message_id=discord_id,
                emoji=react,
                author_id=nick,
                author_display=nick,
            )
            logger.info("IRC reaction bridged: channel={} author={} emoji={}", target, nick, react)
            client._bus.publish("irc", evt)
    elif unreact and reply_to:
        # Remove reaction (IRCv3 +draft/unreact)
        if nick == client.nickname:
            return  # Skip our own echo
        discord_id = client._msgid_tracker.get_discord_id(reply_to)
        if discord_id:
            from bridge.events import reaction_in

            _, evt = reaction_in(
                origin="irc",
                channel_id=f"{client._server}/{target}",
                message_id=discord_id,
                emoji=unreact,
                author_id=nick,
                author_display=nick,
                raw={"is_remove": True},
            )
            logger.info("IRC reaction removal bridged: channel={} author={} emoji={}", target, nick, unreact)
            client._bus.publish("irc", evt)
    elif typing_val == "active":
        from bridge.events import typing_in

        _, evt = typing_in(
            origin="irc",
            channel_id=f"{client._server}/{target}",
            user_id=nick or "unknown",
        )
        client._bus.publish("irc", evt)


async def handle_redact(client: IRCClient, message: object) -> None:
    """Handle IRC REDACT; publish MessageDelete or ReactionIn (removal) for Relay."""
    params = getattr(message, "params", [])
    if len(params) < 2:
        return
    target, irc_msgid = params[0], params[1]
    logger.debug("IRC: received REDACT target={} msgid={}", target, irc_msgid)
    if not target.startswith("#"):
        return
    mapping = client._router.get_mapping_for_irc(client._server, target)
    if not mapping:
        return

    # REDACT on reaction TAGMSG → reaction removal
    reaction_key = client._reaction_tracker.get_reaction_key(irc_msgid)
    if reaction_key:
        discord_id, emoji, author_id = reaction_key
        source = getattr(message, "source", "") or ""
        nick = source.split("!")[0] if "!" in source else source
        from bridge.events import reaction_in

        _, evt = reaction_in(
            origin="irc",
            channel_id=f"{client._server}/{target}",
            message_id=discord_id,
            emoji=emoji,
            author_id=nick or author_id,
            author_display=nick or author_id,
            raw={"is_remove": True},
        )
        logger.info("IRC REDACT (reaction) bridged: channel={} emoji={}", target, emoji)
        client._bus.publish("irc", evt)
        return

    discord_id = client._msgid_tracker.get_discord_id(irc_msgid)
    if not discord_id:
        logger.debug(
            "No Discord msgid for IRC REDACT {}; skip (msgid never stored or expired)",
            irc_msgid,
        )
        return
    source = getattr(message, "source", "") or ""
    nick = source.split("!")[0] if "!" in source else source
    from bridge.events import message_delete

    _, evt = message_delete(
        origin="irc",
        channel_id=f"{client._server}/{target}",
        message_id=discord_id,
        author_id=nick,
        author_display=nick,
    )
    logger.info("IRC REDACT (message) bridged: channel={} msgid={}", target, irc_msgid)
    client._bus.publish("irc", evt)


async def handle_kick(client: IRCClient, channel: str, target: str, by: str, reason: str | None = None) -> None:
    """Handle KICK; rejoin if we were kicked and not banned."""
    if not client._auto_rejoin:
        return
    # Rejoin if we (our nick) were kicked
    if target.lower() != client.nickname.lower():
        return
    if reason and "ban" in reason.lower():
        logger.warning("Not rejoining {} (ban detected)", channel)
        return
    await asyncio.sleep(client._rejoin_delay)
    await client.join(channel)
    logger.info("Rejoined {} after KICK", channel)


async def handle_nick(client: IRCClient, old: str, new: str) -> None:
    """Revert any nick change on the main bridge connection.

    Nick changes are disabled at the server level via restrict-commands, but
    services (SVSNICK) or a race condition could still rename us. Force our
    nick back immediately so the bridge identity stays consistent.

    NOTE: By the time this handler runs, pydle has already updated
    client.nickname to *new*. We compare against the initial nick stored
    at construction time, not the (already-updated) client.nickname.
    """
    initial = getattr(client, "_initial_nick", None)
    if not initial:
        return
    if old.lower() == initial.lower() and new.lower() != initial.lower():
        # Our nick was changed away from the initial — revert it
        logger.warning("IRC: main connection nick changed {} -> {}; reverting to {}", old, new, initial)
        try:
            await client.set_nick(initial)
        except Exception as exc:
            logger.exception("IRC: failed to revert nick change: {}", exc)


async def handle_chghost(client: IRCClient, message: Any) -> None:
    """Handle CHGHOST: user changed username/hostname."""
    # :nick!old_user@old_host CHGHOST new_user new_host
    if len(message.params) >= 2:
        nick = message.source
        new_user = message.params[0]
        new_host = message.params[1]
        logger.debug("IRC CHGHOST: {} -> {}@{}", nick, new_user, new_host)


async def handle_setname(client: IRCClient, message: Any) -> None:
    """Handle SETNAME: user changed realname."""
    # :nick!user@host SETNAME :new realname
    if message.params:
        nick = message.source
        new_realname = message.params[0]
        logger.debug("IRC SETNAME: {} -> {}", nick, new_realname)


# ---------------------------------------------------------------------------
# Puppet nick collision handling (Requirement 20.1, 20.2, 20.3)
# ---------------------------------------------------------------------------

# Default suffixes to try when a nick is in use
_NICK_COLLISION_SUFFIXES = ["[d]", "[1]", "[2]", "[3]", "[4]"]
_MAX_NICK_RETRIES = 5


def _sanitize_nick_for_retry(nick: str) -> str:
    """Re-sanitize a nick by removing characters that may cause ERR_ERRONEUSNICKNAME."""
    # Remove common forbidden characters
    forbidden = set(" \t\n\r!+%@&#$:'\"?*,.")
    cleaned = "".join(c for c in nick if c not in forbidden)
    return cleaned or "user"


def generate_collision_nick(base_nick: str, attempt: int, max_len: int = 23) -> str:
    """Generate an alternative nick for collision avoidance.

    Tries suffixes: [d], [1], [2], ... up to _MAX_NICK_RETRIES.
    Truncates the base nick to fit within max_len.
    """
    if attempt < 0 or attempt >= len(_NICK_COLLISION_SUFFIXES):
        return base_nick[:max_len]
    suffix = _NICK_COLLISION_SUFFIXES[attempt]
    max_base = max_len - len(suffix)
    return base_nick[:max_base] + suffix


async def handle_nick_collision(client: IRCClient, message: object, *, error_code: int) -> None:
    """Handle ERR_NICKNAMEINUSE (433) or ERR_ERRONEUSNICKNAME (432).

    For 433: try alternative nicks with suffix escalation.
    For 432: re-sanitize the nick and retry.
    Falls back to the original nick if all retries are exhausted.
    """
    params = getattr(message, "params", [])
    # params typically: [current_nick, attempted_nick, "Nickname is already in use"]
    attempted_nick = params[1] if len(params) > 1 else client.nickname

    # Track retry attempts on the client
    attempt = getattr(client, "_nick_collision_attempts", 0)
    if not isinstance(attempt, int):
        attempt = 0

    if error_code == 432:
        # ERR_ERRONEUSNICKNAME: re-sanitize and retry
        sanitized = _sanitize_nick_for_retry(attempted_nick)
        if sanitized != attempted_nick:
            logger.warning("IRC: ERR_ERRONEUSNICKNAME for '{}'; retrying with '{}'", attempted_nick, sanitized)
            try:
                await client.set_nick(sanitized)
            except Exception as exc:
                logger.exception("IRC: failed to set sanitized nick '{}': {}", sanitized, exc)
        return

    # ERR_NICKNAMEINUSE (433): try suffix escalation
    if attempt >= _MAX_NICK_RETRIES:
        logger.warning(
            "IRC: all nick collision retries exhausted for '{}'; keeping current nick",
            attempted_nick,
        )
        client._nick_collision_attempts = 0
        return

    # Strip any existing collision suffix to get the base nick
    base = attempted_nick
    for suffix in _NICK_COLLISION_SUFFIXES:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break

    new_nick = generate_collision_nick(base, attempt, max_len=client._server_nicklen)
    client._nick_collision_attempts = attempt + 1
    logger.info(
        "IRC: ERR_NICKNAMEINUSE for '{}'; trying '{}' (attempt {}/{})",
        attempted_nick,
        new_nick,
        attempt + 1,
        _MAX_NICK_RETRIES,
    )
    try:
        await client.set_nick(new_nick)
    except Exception as exc:
        logger.exception("IRC: failed to set collision nick '{}': {}", new_nick, exc)


# ---------------------------------------------------------------------------
# IRC AWAY for offline Discord users (Requirement 24.1, 24.2)
# ---------------------------------------------------------------------------


async def set_puppet_away(client: IRCClient, is_offline: bool) -> None:
    """Set or clear AWAY status on an IRC puppet connection.

    When *is_offline* is True, sends ``AWAY :User is offline on Discord``.
    When False, sends ``AWAY`` with no message to clear the status.
    """
    try:
        if is_offline:
            await client.rawmsg("AWAY", "User is offline on Discord")
            logger.debug("IRC: set AWAY for puppet {}", client.nickname)
        else:
            await client.rawmsg("AWAY")
            logger.debug("IRC: cleared AWAY for puppet {}", client.nickname)
    except Exception as exc:
        logger.debug("IRC: AWAY command failed for {}: {}", client.nickname, exc)
