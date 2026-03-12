"""XMPP inbound event handlers — extracted from XMPPComponent.

All functions receive the component instance as the first parameter,
following the same pattern as the Discord adapter handlers.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any

from loguru import logger
from slixmpp import JID

from bridge.adapters.xmpp.component import SID_NS, _capture_stanza_id_from_echo
from bridge.events import message_in

if TYPE_CHECKING:
    from bridge.adapters.xmpp.component import XMPPComponent


# ---------------------------------------------------------------------------
# Echo suppression utilities (Requirement 17.2)
# ---------------------------------------------------------------------------


def _get_muc_plugin(comp: XMPPComponent):
    """Return the XEP-0045 MUC plugin from the component, or None."""
    plugin_registry = getattr(comp, "plugin", None)
    return plugin_registry.get("xep_0045", None) if plugin_registry else None


def is_xmpp_echo(comp: XMPPComponent, room_jid: str, nick: str) -> bool:
    """Return True if the occupant *nick* in *room_jid* is one of our own puppets.

    Checks the MUC occupant's real JID (via ``get_jid_property``) and compares
    the domain against the component's own JID domain.  This is the primary
    echo-detection mechanism for XMPP MUC messages.

    Returns False when the real JID is unavailable (semi-anonymous MUC) — the
    caller should fall back to :func:`is_recent_echo` in that case.
    """
    if not nick:
        return False
    muc = _get_muc_plugin(comp)
    if not muc:
        return False
    real_jid = muc.get_jid_property(room_jid, nick, "jid")
    if not real_jid:
        return False
    sender_domain = JID(str(real_jid)).domain
    our_domain = JID(comp._component_jid).domain if "@" in comp._component_jid else comp._component_jid
    return sender_domain == our_domain


def is_recent_echo(comp: XMPPComponent, room_jid: str, nick: str) -> bool:
    """Return True if *(room_jid, nick)* was recently used by the bridge to send.

    This is the fallback echo-detection mechanism used when
    ``get_jid_property`` returns ``None`` (the MUC does not expose real JIDs
    to all occupants).
    """
    return (room_jid, nick) in comp._recent_sent_nicks


def is_listener_nick(nick: str) -> bool:
    """Return True if *nick* is the bridge listener nick (never sends content)."""
    return nick == "bridge"


def should_suppress_echo(comp: XMPPComponent, room_jid: str, nick: str) -> bool:
    """Return True if the message from *nick* in *room_jid* should be suppressed.

    Combines all three echo-detection checks in priority order:
    1. Real JID domain match (primary — ``is_xmpp_echo``)
    2. Recent-sent-nicks TTLCache (fallback — ``is_recent_echo``)
    3. Listener nick "bridge" (safety net — ``is_listener_nick``)
    """
    if is_xmpp_echo(comp, room_jid, nick):
        return True
    if is_recent_echo(comp, room_jid, nick):
        return True
    return bool(is_listener_nick(nick))


def on_groupchat_message(comp: XMPPComponent, msg: Any) -> None:
    """Handle MUC message; emit MessageIn."""
    # Skip MUC history playback (delayed delivery)
    if msg.get_plugin("delay", check=True):
        logger.debug("Skipping delayed message (MUC history)")
        return

    body = msg["body"] if msg["body"] else ""
    nick = msg["mucnick"] if msg["mucnick"] else ""
    from_jid = str(msg["from"]) if msg["from"] else ""

    # Convert XMPP spoilers to Discord format
    # XEP-0382: <spoiler>hint</spoiler> — hint is optional warning text
    spoiler_hint: str | None = None
    if msg.get_plugin("spoiler", check=True):
        hint_text = ""
        with contextlib.suppress(AttributeError, TypeError):
            hint_text = (msg["spoiler"].xml.text or "").strip()
        spoiler_hint = hint_text
        body = f"{hint_text}: ||{body}||" if hint_text else f"||{body}||"

    # XEP-0066 OOB: extract file URL from <x xmlns="jabber:x:oob"><url/></x>
    # Clients often put the same URL in both body and oob; avoid duplicating
    if msg.get_plugin("oob", check=True) and msg["oob"]["url"]:
        oob_url = msg["oob"]["url"]
        if body.strip() and oob_url not in body:
            body = body + " " + oob_url
        elif not body.strip():
            body = oob_url

    # XEP-0393 §6: <unstyled xmlns="urn:xmpp:styling:0"/> disables styling
    unstyled = False
    xml = getattr(msg, "xml", None)
    if xml is not None:
        unstyled_elem = xml.find("{urn:xmpp:styling:0}unstyled")
        if unstyled_elem is not None:
            unstyled = True

    if "/" in from_jid:
        room_jid = from_jid.split("/")[0]
        if not nick:
            nick = from_jid.split("/")[1]
    else:
        room_jid = from_jid

    mapping = comp._router.get_mapping_for_xmpp(room_jid)
    if not mapping:
        logger.debug("no mapping for room {}; message from {} not bridged", room_jid, nick)
        return

    # Skip XEP-0424 retraction messages: _on_retraction handles them; do not bridge fallback body
    if msg.get_plugin("retract", check=True):
        return

    # Skip our own echoed messages (from puppets or listener) to prevent doubling
    if is_xmpp_echo(comp, room_jid, nick):
        logger.debug(
            "Echo from our puppet {} in {}; capturing stanza-id for correction mapping",
            nick,
            room_jid,
        )
        _capture_stanza_id_from_echo(comp._msgid_tracker, msg, room_jid)
        return
    if is_recent_echo(comp, room_jid, nick):
        logger.debug("Echo from recent send {} in {} (jid lookup returned None); capturing stanza-id", nick, room_jid)
        _capture_stanza_id_from_echo(comp._msgid_tracker, msg, room_jid)
        return
    if is_listener_nick(nick):
        return  # Listener nick; we never send from it but skip for safety

    # Dedupe: MUC delivers same message to each occupant (listener + puppets)
    msg_id = msg.get("id")
    sid_elem = None  # stanza-id with by=room (for XEP-0444 reactions)
    xml = getattr(msg, "xml", None)
    if xml is not None:
        for elem in xml.iter(f"{{{SID_NS}}}stanza-id"):
            if elem.get("id") and elem.get("by") == room_jid:
                sid_elem = elem
                break
        if sid_elem is None:
            first_sid = xml.find(f".//{{{SID_NS}}}stanza-id")
            if first_sid is not None and first_sid.get("id"):
                sid_elem = first_sid
        if sid_elem is not None and sid_elem.get("id"):
            msg_id = msg_id or sid_elem.get("id")
    if msg_id:
        dedupe_key = (room_jid, str(msg_id))
        if dedupe_key in comp._seen_msg_ids:
            logger.debug("Skipping duplicate MUC delivery for {}", dedupe_key)
            return
        comp._seen_msg_ids[dedupe_key] = None

    # Check for message correction (XEP-0308)
    is_edit = False
    replace_id = None
    if msg.get_plugin("replace", check=True):
        replace_id = msg["replace"]["id"]
        is_edit = True
        logger.debug("Received XMPP correction for message {}", replace_id)

    # Check for reply reference (XEP-0461 or XEP-0372)
    reply_to_xmpp_id: str | None = None
    reply_quoted_author: str | None = None

    # Try XEP-0461 first (newer)
    if msg.get_plugin("reply", check=True):
        reply_plugin = msg["reply"]
        if reply_plugin.get("id"):
            reply_to_xmpp_id = reply_plugin["id"]
            logger.debug("Received XMPP reply (XEP-0461) to message {}", reply_to_xmpp_id)
            # Extract author nick from the reply's 'to' attribute (full MUC JID: room/nick)
            reply_to_jid = reply_plugin.get("to")
            if reply_to_jid:
                reply_to_str = str(reply_to_jid)
                if "/" in reply_to_str:
                    reply_quoted_author = reply_to_str.split("/", 1)[1]

    # Fall back to XEP-0372 if no XEP-0461 reply
    if not reply_to_xmpp_id and msg.get_plugin("reference", check=True):
        ref = msg["reference"]
        if ref.get("type") == "reply" and ref.get("uri"):
            # Extract message ID from URI (format: xmpp:room@server?id=msgid)
            uri = ref["uri"]
            if "?id=" in uri:
                reply_to_xmpp_id = uri.split("?id=")[1]
                logger.debug("Received XMPP reply (XEP-0372) to message {}", reply_to_xmpp_id)

    # Resolve XMPP stanza-id to Discord ID for relay (IRC/XMPP adapters need canonical ID)
    reply_to_id: str | None = None
    if reply_to_xmpp_id:
        reply_to_id = comp._msgid_tracker.get_discord_id(reply_to_xmpp_id)
        if reply_to_id:
            logger.debug("Resolved XMPP reply target {} -> Discord {}", reply_to_xmpp_id, reply_to_id)

    # Get or generate message ID. XEP-0444 §4.2: for groupchat, MUST use stanza-id, NOT
    # the top-level id. Reactions in MUC require the stanza-id from the MUC server because
    # that's the ID other participants see. The top-level id (origin-id) is only visible
    # to the sender and the server.
    stanza_id_val = sid_elem.get("id") if sid_elem is not None and sid_elem.get("id") else None
    top_level_id = msg.get("id")
    xmpp_msg_id = str(stanza_id_val) if stanza_id_val else (top_level_id or f"xmpp:{room_jid}:{nick}:{id(msg)}")

    # Collect ID aliases for edit lookup: clients may use origin-id or top-level id for
    # replace_id in corrections; we must resolve any of them to Discord.
    origin_id_val = None
    if xml is not None:
        origin_id_elem = xml.find(f".//{{{SID_NS}}}origin-id")
        if origin_id_elem is not None and origin_id_elem.get("id"):
            origin_id_val = origin_id_elem.get("id")

    raw_data: dict[str, Any] = {}
    if unstyled:
        raw_data["unstyled"] = True
    if spoiler_hint is not None:
        raw_data["spoiler_hint"] = spoiler_hint
    if replace_id:
        raw_data["replace_id"] = replace_id
    if reply_to_xmpp_id:
        raw_data["reply_to_id"] = reply_to_xmpp_id  # Original XMPP stanza-id (for tests/debug)
        if reply_quoted_author:
            raw_data["reply_quoted_author"] = reply_quoted_author
        # Extract quoted content from XEP-0428 fallback so relay can add > quote for IRC
        if xml is not None:
            fb = xml.find(".//{urn:xmpp:fallback:0}fallback[@for='urn:xmpp:reply:0']")
            if fb is not None:
                body_region = fb.find("{urn:xmpp:fallback:0}body")
                if body_region is not None:
                    start = body_region.get("start")
                    end = body_region.get("end")
                    if start is not None and end is not None:
                        try:
                            s, e = int(start), int(end)
                            if 0 <= s < e <= len(body):
                                raw_data["reply_quoted_content"] = body[s:e]
                        except (ValueError, TypeError):
                            pass
    aliases = []
    for aid in (origin_id_val, top_level_id):
        if aid and aid != xmpp_msg_id and aid not in aliases:
            aliases.append(aid)
    if aliases:
        raw_data["xmpp_id_aliases"] = aliases

    # Build avatar URL: try PEP first, then vCard as fallback. Base from room domain (muc.atl.chat → atl.chat);
    # path from real JID localpart (alice@atl.chat → /pep_avatar/alice). User domain irrelevant.
    avatar_url: str | None = None
    muc = _get_muc_plugin(comp)
    if muc and nick:
        real_jid = muc.get_jid_property(room_jid, nick, "jid")
        if real_jid:
            room_domain = JID(room_jid).domain
            base_domain = room_domain[4:] if room_domain.startswith("muc.") else room_domain
            node = JID(str(real_jid)).local
            avatar_url = comp._resolve_avatar_url(base_domain, node)

    _, evt = message_in(
        origin="xmpp",
        channel_id=room_jid,
        author_id=nick,
        author_display=nick,
        content=body,
        message_id=xmpp_msg_id,
        reply_to_id=reply_to_id,
        is_edit=is_edit,
        is_action=False,
        avatar_url=avatar_url,
        raw=raw_data if raw_data else {},
    )
    logger.info("message bridged: room={} author={}", room_jid, nick)
    comp._bus.publish("xmpp", evt)


def on_reactions(comp: XMPPComponent, msg: Any) -> None:
    """Handle XMPP reactions; emit to bus."""
    from_jid = str(msg["from"]) if msg["from"] else ""
    if "/" in from_jid:
        room_jid = from_jid.split("/")[0]
        nick = from_jid.split("/")[1]
    else:
        return

    mapping = comp._router.get_mapping_for_xmpp(room_jid)
    if not mapping:
        return

    # Skip our own echoed reactions (from puppets) to prevent doubling
    if should_suppress_echo(comp, room_jid, nick):
        logger.debug("skipping reaction echo from our component ({})", nick)
        return

    reactions = msg.get_plugin("reactions", check=True)
    if not reactions:
        return

    target_msg_id = reactions.get("id")
    if not target_msg_id:
        return

    emojis_raw = reactions.get_values()
    new_set = frozenset(e for e in emojis_raw if e and isinstance(e, str))
    # XEP-0444 sends the FULL reaction set per-user per-message on every update.
    # We diff against the previous set to determine which reactions were added
    # and which were removed, then emit individual add/remove events.
    cache_key = (target_msg_id, nick)
    prev_set = comp._reactions_by_user.get(cache_key, frozenset())
    comp._reactions_by_user[cache_key] = new_set

    discord_id = comp._msgid_tracker.get_discord_id(target_msg_id)
    if not discord_id:
        logger.debug("No Discord msgid for XMPP reaction on {}; skip", target_msg_id)
        return

    from bridge.events import reaction_in

    removed = prev_set - new_set
    added = new_set - prev_set
    for emoji in removed:
        _, evt = reaction_in(
            origin="xmpp",
            channel_id=room_jid,
            message_id=discord_id,
            emoji=emoji,
            author_id=nick,
            author_display=nick,
            raw={"is_remove": True},
        )
        logger.info("reaction removal bridged: room={} author={} emoji={}", room_jid, nick, emoji)
        comp._bus.publish("xmpp", evt)
    for emoji in added:
        _, evt = reaction_in(
            origin="xmpp",
            channel_id=room_jid,
            message_id=discord_id,
            emoji=emoji,
            author_id=nick,
            author_display=nick,
        )
        logger.info("reaction bridged: room={} author={} emoji={}", room_jid, nick, emoji)
        comp._bus.publish("xmpp", evt)


async def _send_moderation_for_retraction(comp: XMPPComponent, room_jid: str, target_msg_id: str) -> None:
    """Send XEP-0425 moderation request so Dino (and similar) delete locally. Fire-and-forget."""
    try:
        plugin = comp.plugin.get("xep_0425", None)
        if plugin:
            # Component must set explicit 'from' for Prosody; otherwise stream error (invalid-from).
            await plugin.moderate(JID(room_jid), target_msg_id, ifrom=JID(comp._component_jid))
            logger.debug("sent moderation for retraction {} in {}", target_msg_id, room_jid)
    except Exception as exc:
        logger.debug(
            "moderation for retraction {} failed (bridge may not be moderator): {}",
            target_msg_id,
            exc,
        )


def on_retraction(comp: XMPPComponent, msg: Any) -> None:
    """Handle XMPP message retraction; emit to bus."""
    from bridge.config import cfg

    from_jid = str(msg["from"]) if msg["from"] else ""
    if "/" in from_jid:
        room_jid = from_jid.split("/")[0]
        nick = from_jid.split("/")[1]
    else:
        # Bare room JID — likely a XEP-0425 moderation announcement
        room_jid = from_jid
        mapping = comp._router.get_mapping_for_xmpp(room_jid)
        if mapping:
            try_handle_moderation(comp, msg, room_jid)
        return

    mapping = comp._router.get_mapping_for_xmpp(room_jid)
    if not mapping:
        return

    # Skip our own echoed retractions (from puppets) to prevent loop/doubling
    if should_suppress_echo(comp, room_jid, nick):
        logger.debug("skipping retraction echo from our component ({})", nick)
        return

    retract = msg.get_plugin("retract", check=True)
    if not retract:
        return

    target_msg_id = retract.get("id")

    # Dedupe: MUC delivers to each occupant (listener + puppets)
    dedupe_key = f"{room_jid}:{target_msg_id}"
    if dedupe_key in comp._seen_retraction_ids:
        return
    comp._seen_retraction_ids[dedupe_key] = None

    discord_id = comp._msgid_tracker.get_discord_id(target_msg_id)
    if not discord_id:
        logger.debug("no Discord msgid for retraction {}; skip", target_msg_id)
        return

    from bridge.events import message_delete

    _, evt = message_delete(
        origin="xmpp",
        channel_id=room_jid,
        message_id=discord_id,
        author_id=nick or "",
        author_display=nick or "",
    )
    logger.info("retraction bridged: room={} author={} message={}", room_jid, nick, target_msg_id)
    comp._bus.publish("xmpp", evt)

    # Option 1 hack: also send XEP-0425 moderation so Dino (and similar clients) delete locally.
    # Requires bridge component JID to be a MUC moderator.
    if cfg.xmpp_promote_retraction_to_moderation and target_msg_id:
        comp._recently_moderated_by_us[dedupe_key] = None
        task = asyncio.create_task(_send_moderation_for_retraction(comp, room_jid, target_msg_id))
        comp._moderation_tasks.add(task)
        task.add_done_callback(comp._moderation_tasks.discard)


def on_moderated_message(comp: XMPPComponent, msg: Any) -> None:
    """Handle XEP-0425 moderator retraction; emit delete to bus."""
    from_jid = str(msg["from"]) if msg["from"] else ""
    # XEP-0425 §5: only moderation from the MUC service (bare room JID) is legitimate
    if "/" in from_jid:
        return  # From occupant; discard (spoofing)
    room_jid = from_jid
    if not room_jid:
        return

    mapping = comp._router.get_mapping_for_xmpp(room_jid)
    if not mapping:
        return

    retract = msg.get_plugin("retract", check=True)
    if not retract:
        return

    target_msg_id = retract.get("id")
    if not target_msg_id:
        logger.debug("XEP-0425 moderation missing retract id; skip")
        return

    # Skip when we initiated this moderation (XEP-0424→0425 promotion); already relayed
    dedupe_key = f"{room_jid}:{target_msg_id}"
    if dedupe_key in comp._recently_moderated_by_us:
        logger.debug("skipping moderation echo for {} (we initiated)", target_msg_id)
        return

    # Dedupe: multiple handlers and MUC occupant copies fire for the same moderation
    if dedupe_key in comp._seen_moderation_ids:
        return
    comp._seen_moderation_ids[dedupe_key] = None

    discord_id = comp._msgid_tracker.get_discord_id(target_msg_id)
    if not discord_id:
        logger.debug("No Discord msgid for moderated retraction {}; skip", target_msg_id)
        return

    # Extract moderator info from <moderated by="..."/>
    moderated = retract.get_plugin("moderated", check=True)
    moderator = str(moderated["by"]) if moderated else "moderator"

    from bridge.events import message_delete

    _, evt = message_delete(
        origin="xmpp",
        channel_id=room_jid,
        message_id=discord_id,
        author_id=moderator,
        author_display=moderator,
    )
    logger.info("moderation bridged: room={} moderator={} message={}", room_jid, moderator, target_msg_id)
    comp._bus.publish("xmpp", evt)


def try_handle_moderation(comp: XMPPComponent, msg: Any, room_jid: str) -> None:
    """Check if a retraction message is actually a XEP-0425 moderation and bridge it."""
    xml = msg.xml if hasattr(msg, "xml") else None
    if xml is None:
        return

    target_msg_id: str | None = None
    moderator: str = "moderator"

    # Try v1 first: <retract xmlns="urn:xmpp:message-retract:1" id="..."><moderated .../>
    for retract_el in xml.findall("{urn:xmpp:message-retract:1}retract"):
        mod_el = retract_el.find("{urn:xmpp:message-moderate:1}moderated")
        if mod_el is not None:
            target_msg_id = retract_el.get("id")
            moderator = mod_el.get("by", "moderator")
            break

    # Fallback to v0: <apply-to xmlns="urn:xmpp:fasten:0" id="..."><moderated .../>
    if not target_msg_id:
        for apply_el in xml.findall("{urn:xmpp:fasten:0}apply-to"):
            mod_el = apply_el.find("{urn:xmpp:message-moderate:0}moderated")
            if mod_el is not None:
                target_msg_id = apply_el.get("id")
                moderator = mod_el.get("by", "moderator")
                break

    if not target_msg_id:
        return

    # Dedupe: MUC delivers to each occupant and multiple handlers fire per stanza
    dedupe_key = f"{room_jid}:{target_msg_id}"
    # Skip when we initiated this moderation (XEP-0424→0425 promotion); already relayed
    if dedupe_key in comp._recently_moderated_by_us:
        return
    if dedupe_key in comp._seen_moderation_ids:
        return
    comp._seen_moderation_ids[dedupe_key] = None

    discord_id = comp._msgid_tracker.get_discord_id(target_msg_id)
    if not discord_id:
        logger.debug(
            "No Discord msgid for moderated retraction {}; skip",
            target_msg_id,
        )
        return

    from bridge.events import message_delete

    _, evt = message_delete(
        origin="xmpp",
        channel_id=room_jid,
        message_id=discord_id,
        author_id=moderator,
        author_display=moderator,
    )
    logger.info("moderation bridged: room={} moderator={} target={}", room_jid, moderator, target_msg_id)
    comp._bus.publish("xmpp", evt)


def on_raw_groupchat(comp: XMPPComponent, msg: Any) -> None:
    """Catch ALL groupchat stanzas to intercept bodyless moderation announcements."""
    xml = msg.xml if hasattr(msg, "xml") else None
    if xml is None:
        return

    # If the message has a <body>, the normal groupchat_message handler
    # will fire — skip to avoid double-processing.
    body_el = xml.find("{jabber:component:accept}body")
    if body_el is None:
        body_el = xml.find("{jabber:client}body")
    if body_el is None:
        body_el = xml.find("body")
    if body_el is not None and (body_el.text or "").strip():
        return

    # Check for moderation elements (v0 or v1)
    has_moderation = False
    for _el in xml.findall("{urn:xmpp:message-retract:1}retract"):
        if _el.find("{urn:xmpp:message-moderate:1}moderated") is not None:
            has_moderation = True
            break
    if not has_moderation:
        for _el in xml.findall("{urn:xmpp:fasten:0}apply-to"):
            if _el.find("{urn:xmpp:message-moderate:0}moderated") is not None:
                has_moderation = True
                break

    if not has_moderation:
        return

    from_val = msg["from"] if hasattr(msg, "__getitem__") else None
    from_jid = str(from_val) if from_val else (str(xml.get("from", "")) if xml is not None else "")
    # XEP-0425 §5: only moderation from the MUC service (bare room JID) is legitimate
    if "/" in from_jid:
        return  # From occupant; discard (spoofing)
    room_jid = from_jid
    if not room_jid:
        return

    mapping = comp._router.get_mapping_for_xmpp(room_jid)
    if not mapping:
        return

    logger.debug("Raw groupchat moderation detected in {}", room_jid)
    try_handle_moderation(comp, msg, room_jid)


def on_ibb_stream_start(comp: XMPPComponent, stream: Any) -> None:
    """Handle incoming IBB stream; log for now."""
    logger.info(
        "IBB stream from {}: sid={} block_size={}",
        stream.peer,
        stream.sid,
        stream.block_size,
    )
    # Start async handler for this stream
    task = asyncio.create_task(handle_ibb_stream(comp, stream))
    comp._ibb_streams[stream.sid] = task


def on_ibb_stream_end(comp: XMPPComponent, stream: Any) -> None:
    """Handle IBB stream end."""
    logger.info("IBB stream ended: sid={}", stream.sid)
    if stream.sid in comp._ibb_streams:
        comp._ibb_streams[stream.sid].cancel()
        del comp._ibb_streams[stream.sid]


async def handle_ibb_stream(comp: XMPPComponent, stream: Any) -> None:
    """Receive IBB stream data and bridge to Discord/IRC."""
    try:
        # Gather all data (max 10MB, 5min timeout)
        data = await stream.gather(max_data=10 * 1024 * 1024, timeout=300)
        logger.info(
            "Received {} bytes from {} (sid={})",
            len(data),
            stream.peer,
            stream.sid,
        )

        # Extract room from peer JID if it's a MUC participant
        peer_str = str(stream.peer)
        if "/" in peer_str:
            room_jid = peer_str.split("/", maxsplit=1)[0]
            nick = peer_str.split("/")[1]
        else:
            room_jid = peer_str
            nick = "unknown"

        # Find mapping for this room
        mapping = comp._router.get_mapping_for_xmpp(room_jid)
        if not mapping:
            logger.warning("no mapping for room {}", room_jid)
            return

        # Publish a message event through the bus so the relay routes to
        # all targets (Discord, IRC).  We no longer import DiscordAdapter
        # directly — adapter isolation (Requirement 8.3).
        _, evt = message_in(
            origin="xmpp",
            channel_id=mapping.discord_channel_id,
            author_id=nick,
            author_display=nick,
            content=f"📎 [File received via XMPP: {len(data)} bytes]",
            message_id=f"xmpp:ibb:{stream.sid}",
            is_action=False,
        )
        comp._bus.publish("xmpp", evt)

    except TimeoutError:
        logger.warning("IBB stream timeout: sid={}", stream.sid)
    except Exception as exc:
        logger.exception("IBB stream error: {}", exc)
    finally:
        if stream.sid in comp._ibb_streams:
            del comp._ibb_streams[stream.sid]


# ---------------------------------------------------------------------------
# MUC presence / status code handling (Requirement 26)
# ---------------------------------------------------------------------------

MUC_USER_NS = "http://jabber.org/protocol/muc#user"


def _extract_status_codes(presence: Any) -> set[int]:
    """Extract MUC status codes from a presence stanza.

    Status codes live inside ``<x xmlns='http://jabber.org/protocol/muc#user'>``
    as ``<status code='NNN'/>`` elements.
    """
    codes: set[int] = set()
    x_elem = presence.xml.find(f"{{{MUC_USER_NS}}}x")
    if x_elem is None:
        return codes
    for status_el in x_elem.findall(f"{{{MUC_USER_NS}}}status"):
        code_str = status_el.get("code")
        if code_str and code_str.isdigit():
            codes.add(int(code_str))
    return codes


def _extract_nick_from_presence(presence: Any) -> str:
    """Extract the nick (resource part) from a MUC presence 'from' JID."""
    from_jid = str(presence.get("from", ""))
    if "/" in from_jid:
        return from_jid.split("/", maxsplit=1)[1]
    return ""


def _extract_room_jid(presence: Any) -> str:
    """Extract the bare room JID from a MUC presence 'from' JID."""
    from_jid = str(presence.get("from", ""))
    if "/" in from_jid:
        return from_jid.split("/", maxsplit=1)[0]
    return from_jid


def on_muc_presence(comp: XMPPComponent, presence: Any) -> None:
    """Handle MUC presence stanzas with status codes.

    Status codes handled:
    - 110: Self-presence — confirm join is complete (Req 26.1)
    - 210: Nick modified by server (Req 26.2)
    - 301: Banned from MUC (Req 26.3)
    - 307: Kicked from MUC (Req 26.4)
    - 321/322/332: Removal / shutdown (Req 26.5)
    """
    codes = _extract_status_codes(presence)
    if not codes:
        return

    room_jid = _extract_room_jid(presence)
    nick = _extract_nick_from_presence(presence)

    # --- Status 110: Self-presence (join confirmed) ---
    if 110 in codes:
        comp._confirmed_mucs.add(room_jid)
        logger.info("MUC join confirmed (status 110) for {} in {}", nick, room_jid)

        # Status 210 often accompanies 110 when the server modified the nick
        if 210 in codes:
            _handle_nick_modified(comp, room_jid, nick)
        return

    # --- Status 210: Nick modified by server ---
    if 210 in codes:
        _handle_nick_modified(comp, room_jid, nick)
        return

    # --- Status 301: Banned ---
    if 301 in codes:
        comp._banned_rooms.add(room_jid)
        # Remove from puppet tracking
        _remove_puppet_entries(comp, room_jid)
        comp._confirmed_mucs.discard(room_jid)
        logger.warning("Banned from MUC {} (status 301) — will not attempt rejoin", room_jid)
        return

    # --- Status 307: Kicked ---
    if 307 in codes:
        _remove_puppet_entries(comp, room_jid)
        comp._confirmed_mucs.discard(room_jid)
        logger.warning("Kicked from MUC {} (status 307)", room_jid)
        if comp._auto_rejoin:
            _schedule_rejoin(comp, room_jid)
        return

    # --- Status 321/322/332: Removal / shutdown ---
    removal_codes = codes & {321, 322, 332}
    if removal_codes:
        _remove_puppet_entries(comp, room_jid)
        comp._confirmed_mucs.discard(room_jid)
        for code in sorted(removal_codes):
            if code == 332:
                logger.warning("Removed from MUC {} due to server shutdown (status 332)", room_jid)
            elif code == 321:
                logger.warning("Removed from MUC {} due to affiliation change (status 321)", room_jid)
            elif code == 322:
                logger.warning("Removed from MUC {} — room now members-only (status 322)", room_jid)

        # Attempt rejoin for 321/322 (affiliation/members-only) but NOT 332 (shutdown)
        if removal_codes <= {321, 322} and comp._auto_rejoin:
            _schedule_rejoin(comp, room_jid)


def _handle_nick_modified(comp: XMPPComponent, room_jid: str, new_nick: str) -> None:
    """Update internal nick tracking when the server modifies a nick (status 210)."""
    logger.info("Nick modified by server in {} — now '{}'", room_jid, new_nick)
    # The puppet tracking uses (muc_jid, user_jid) tuples, so the nick change
    # doesn't invalidate those entries. But we log it for observability.
    # If the component's own listener nick was changed, we note it.


def _remove_puppet_entries(comp: XMPPComponent, room_jid: str) -> None:
    """Remove all puppet join entries for a given MUC room."""
    to_remove = {key for key in comp._puppets_joined if key[0] == room_jid}
    comp._puppets_joined -= to_remove


def _schedule_rejoin(comp: XMPPComponent, room_jid: str) -> None:
    """Schedule an async rejoin attempt for a MUC room."""
    logger.info("Scheduling rejoin for MUC {}", room_jid)
    asyncio.ensure_future(_rejoin_muc(comp, room_jid))  # noqa: RUF006


async def _rejoin_muc(comp: XMPPComponent, room_jid: str) -> None:
    """Attempt to rejoin a MUC after a short delay."""
    await asyncio.sleep(5)  # Brief delay before rejoin attempt
    if room_jid in comp._banned_rooms:
        logger.debug("Skipping rejoin for {} — room is in banned list", room_jid)
        return
    try:
        muc_plugin = comp.plugin.get("xep_0045", None)
        if muc_plugin:
            bridge_nick = "bridge"
            bridge_jid = f"bridge@{comp._component_jid}"
            await muc_plugin.join_muc_wait(
                JID(room_jid),
                bridge_nick,
                presence_options={"pfrom": JID(bridge_jid)},
                timeout=30,
                maxchars=0,
            )
            logger.info("Rejoined MUC {} after removal", room_jid)
    except Exception as exc:
        logger.warning("Failed to rejoin MUC {}: {}", room_jid, exc)
