"""XMPP component: per-Discord-user JIDs with ComponentXMPP."""

from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from typing import TYPE_CHECKING, Any

import aiohttp
from cachetools import TTLCache
from loguru import logger
from slixmpp import JID
from slixmpp.componentxmpp import ComponentXMPP
from slixmpp.exceptions import XMPPError

from bridge.adapters.xmpp_msgid import XMPPMessageIDTracker
from bridge.events import message_in
from bridge.gateway import Bus, ChannelRouter

# XEP-0106 JID escape map: chars disallowed by nodeprep -> escape sequence.
# slixmpp's XEP_0106 plugin only advertises disco; it has no escape API.
_JID_ESCAPE_MAP = {
    " ": "\\20",
    '"': "\\22",
    "&": "\\26",
    "'": "\\27",
    "/": "\\2f",
    ":": "\\3a",
    "<": "\\3c",
    ">": "\\3e",
    "@": "\\40",
    "\\": "\\5c",
}


def _escape_jid_node(node: str) -> str:
    """Escape a JID node (localpart) per XEP-0106 for characters disallowed by nodeprep."""
    return "".join(_JID_ESCAPE_MAP.get(c, c) for c in node)


SID_NS = "urn:xmpp:sid:0"


def _capture_stanza_id_from_echo(tracker: XMPPMessageIDTracker, msg: Any, room_jid: str) -> None:
    """Capture IDs from our echo for correction mapping.

    Prosody adds stanza-id as a child element but may not rewrite the top-level
    msg id. Gajim and many clients use the top-level id for XEP-0308 matching,
    so we keep our_id (origin-id) for corrections. We only update to stanza-id
    when msg.id was rewritten (stanza_id != our_id and msg.id == stanza_id),
    indicating the server rewrote the id for delivery.
    """
    xml = getattr(msg, "xml", None)
    if xml is None:
        logger.debug("Echo capture: no xml on msg")
        return
    origin_id_elem = xml.find(f".//{{{SID_NS}}}origin-id")
    our_id = origin_id_elem.get("id") if origin_id_elem is not None else None
    if not our_id:
        our_id = msg.get("id")
    msg_id_attr = msg.get("id")
    stanza_id_elem = xml.find(f".//{{{SID_NS}}}stanza-id")
    stanza_id = stanza_id_elem.get("id") if stanza_id_elem is not None else None
    if not stanza_id:
        stanza_id = msg_id_attr

    logger.debug(
        "Echo capture: room={} origin_id={} msg.id={} stanza_id={}",
        room_jid,
        our_id,
        msg_id_attr,
        stanza_id,
    )

    if not our_id:
        return
    # Corrections: keep our_id (Gajim uses top-level id). Reactions: add stanza-id as alias.
    if stanza_id and stanza_id != our_id and tracker.add_stanza_id_alias(our_id, stanza_id):
        logger.debug(
            "Added stanza-id alias {} for reactions (corrections still use our_id {})",
            stanza_id,
            our_id,
        )
    # Only replace our_id for corrections when server rewrote top-level id
    if stanza_id and stanza_id != our_id and msg_id_attr == stanza_id and tracker.update_xmpp_id(our_id, stanza_id):
        logger.info(
            "Updated msgid mapping {} -> {} (server rewrote id); corrections use stanza-id",
            our_id,
            stanza_id,
        )


if TYPE_CHECKING:
    from bridge.identity import IdentityResolver


class XMPPComponent(ComponentXMPP):
    """XMPP component for multi-presence bridge (puppets)."""

    def __init__(
        self,
        jid: str,
        secret: str,
        server: str,
        port: int,
        bus: Bus,
        router: ChannelRouter,
        identity: IdentityResolver | None,
    ):
        ComponentXMPP.__init__(self, jid, secret, server, port)
        self._bus = bus
        self._router = router
        self._identity = identity
        self._component_jid = jid
        self._avatar_cache: TTLCache[str, str] = TTLCache(
            maxsize=1000, ttl=86400
        )  # discord_id -> avatar_hash (24h TTL)
        self._session: aiohttp.ClientSession | None = None
        self._ibb_streams: dict[str, asyncio.Task] = {}  # sid -> handler task
        self._msgid_tracker = XMPPMessageIDTracker()  # Track message IDs for edits
        self._puppets_joined: set[tuple[str, str]] = set()  # (muc_jid, user_jid) — avoid re-join
        # Dedupe: MUC delivers same message to each occupant (listener + puppets) — process once
        self._seen_msg_ids: TTLCache[tuple[str, str], None] = TTLCache(maxsize=500, ttl=60)
        # Fallback echo detection when get_jid_property returns None (MUC may not expose real JID)
        self._recent_sent_nicks: TTLCache[tuple[str, str], None] = TTLCache(maxsize=200, ttl=10)
        # XEP-0444: track per-user reaction sets to detect removals (full set sent each update)
        self._reactions_by_user: TTLCache[tuple[str, str], frozenset[str]] = TTLCache(maxsize=2000, ttl=3600)

        # Register XEPs
        self.register_plugin("xep_0030")  # Service Discovery
        self.register_plugin("xep_0045")  # Multi-User Chat
        self.register_plugin("xep_0198")  # Stream Management
        self.register_plugin("xep_0199")  # XMPP Ping
        self.register_plugin("xep_0203")  # Delayed Delivery
        self.register_plugin("xep_0308")  # Last Message Correction
        self.register_plugin("xep_0359")  # Unique Stanza IDs (origin-id for echo capture)
        self.register_plugin("xep_0054")  # vCard-temp
        self.register_plugin("xep_0047")  # In-Band Bytestreams
        self.register_plugin("xep_0363")  # HTTP File Upload
        self.register_plugin("xep_0372")  # References
        self.register_plugin("xep_0382")  # Spoiler Messages
        self.register_plugin("xep_0422")  # Message Fastening
        self.register_plugin("xep_0424")  # Message Retraction
        self.register_plugin("xep_0444")  # Message Reactions
        self.register_plugin("xep_0461")  # Message Replies
        self.register_plugin("xep_0106")  # JID Escaping

        # Enable stream resumption for network resilience
        self.plugin["xep_0198"].allow_resume = True

        # Enable keepalive pings to detect dead connections
        self.plugin["xep_0199"].enable_keepalive(interval=180, timeout=30)

        # Add component identity for service discovery
        disco = self.plugin.get("xep_0030", None)
        if disco:
            disco.add_identity(
                category="gateway",
                itype="discord",
                name="Discord-IRC-XMPP Bridge",
            )

        self.add_event_handler("groupchat_message", self._on_groupchat_message)
        self.add_event_handler("reactions", self._on_reactions)
        self.add_event_handler("message_retract", self._on_retraction)
        self.add_event_handler("ibb_stream_start", self._on_ibb_stream_start)
        self.add_event_handler("ibb_stream_end", self._on_ibb_stream_end)
        self.add_event_handler("session_start", self._on_session_start)
        self.add_event_handler("disconnected", self._on_disconnected)

    async def _on_session_start(self, event: Any) -> None:
        """Initialize HTTP session and join MUCs for receiving messages."""
        if not self._session:
            self._session = aiohttp.ClientSession()

        # Join all mapped MUCs so we receive groupchat_message events (XMPP → Discord/IRC)
        muc_plugin = self.plugin.get("xep_0045", None)
        if muc_plugin:
            bridge_nick = "atl-bridge"
            bridge_jid = f"bridge@{self._component_jid}"
            for mapping in self._router.all_mappings():
                if mapping.xmpp:
                    try:
                        await muc_plugin.join_muc_wait(  # type: ignore[misc,call-arg]
                            JID(mapping.xmpp.muc_jid),
                            bridge_nick,
                            presence_options={"pfrom": JID(bridge_jid)},
                            timeout=30,
                            maxchars=0,  # Skip MUC history to avoid flooding
                        )
                        logger.info("Joined MUC {} as listener ({})", mapping.xmpp.muc_jid, bridge_nick)
                    except XMPPError as exc:
                        logger.warning("Failed to join MUC {}: {}", mapping.xmpp.muc_jid, exc)

    async def _on_disconnected(self, event: Any) -> None:
        """Close HTTP session on XMPP disconnect."""
        if self._session:
            await self._session.close()
            self._session = None

    def _on_groupchat_message(self, msg: Any) -> None:
        """Handle MUC message; emit MessageIn."""
        # Skip MUC history playback (delayed delivery)
        if msg.get_plugin("delay", check=True):
            logger.debug("Skipping delayed message (MUC history)")
            return

        body = msg["body"] if msg["body"] else ""
        nick = msg["mucnick"] if msg["mucnick"] else ""
        from_jid = str(msg["from"]) if msg["from"] else ""

        # Convert XMPP spoilers to Discord format
        if msg.get_plugin("spoiler", check=True):
            body = f"||{body}||"

        if "/" in from_jid:
            room_jid = from_jid.split("/")[0]
            if not nick:
                nick = from_jid.split("/")[1]
        else:
            room_jid = from_jid

        mapping = self._router.get_mapping_for_xmpp(room_jid)
        if not mapping:
            logger.debug("XMPP: no mapping for room {}; message from {} not bridged", room_jid, nick)
            return

        # Skip our own echoed messages (from puppets or listener) to prevent doubling
        plugin_registry = getattr(self, "plugin", None)
        muc = plugin_registry.get("xep_0045", None) if plugin_registry else None
        if muc and nick:
            real_jid = muc.get_jid_property(room_jid, nick, "jid")
            if real_jid:
                sender_domain = JID(str(real_jid)).domain
                our_domain = JID(self._component_jid).domain if "@" in self._component_jid else self._component_jid
                if sender_domain == our_domain:
                    logger.debug(
                        "Echo from our puppet {} in {}; capturing stanza-id for correction mapping",
                        nick,
                        room_jid,
                    )
                    _capture_stanza_id_from_echo(self._msgid_tracker, msg, room_jid)
                    return
        # Fallback: get_jid_property may return None (MUC may not expose real JID to all occupants)
        if (room_jid, nick) in self._recent_sent_nicks:
            logger.debug("Echo from recent send {} in {} (jid lookup returned None); skipping", nick, room_jid)
            return
        if nick == "atl-bridge":
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
            if dedupe_key in self._seen_msg_ids:
                logger.debug("Skipping duplicate MUC delivery for {}", dedupe_key)
                return
            self._seen_msg_ids[dedupe_key] = None

        # Check for message correction (XEP-0308)
        is_edit = False
        replace_id = None
        if msg.get_plugin("replace", check=True):
            replace_id = msg["replace"]["id"]
            is_edit = True
            logger.debug("Received XMPP correction for message {}", replace_id)

        # Check for reply reference (XEP-0461 or XEP-0372)
        reply_to_id = None

        # Try XEP-0461 first (newer)
        if msg.get_plugin("reply", check=True):
            reply_plugin = msg["reply"]
            if reply_plugin.get("id"):
                reply_to_id = reply_plugin["id"]
                logger.debug("Received XMPP reply (XEP-0461) to message {}", reply_to_id)

        # Fall back to XEP-0372 if no XEP-0461 reply
        if not reply_to_id and msg.get_plugin("reference", check=True):
            ref = msg["reference"]
            if ref.get("type") == "reply" and ref.get("uri"):
                # Extract message ID from URI (format: xmpp:room@server?id=msgid)
                uri = ref["uri"]
                if "?id=" in uri:
                    reply_to_id = uri.split("?id=")[1]
                    logger.debug("Received XMPP reply (XEP-0372) to message {}", reply_to_id)

        # Get or generate message ID. XEP-0444 §4.2: for groupchat, MUST use stanza-id, NOT
        # the top-level id. Reactions in MUC require the stanza-id from the MUC server.
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

        raw_data = {}
        if replace_id:
            raw_data["replace_id"] = replace_id
        if reply_to_id:
            raw_data["reply_to_id"] = reply_to_id
        aliases = []
        for aid in (origin_id_val, top_level_id):
            if aid and aid != xmpp_msg_id and aid not in aliases:
                aliases.append(aid)
        if aliases:
            raw_data["xmpp_id_aliases"] = aliases

        # Build avatar URL from mod_http_avatar. Base from room domain (muc.atl.chat → atl.chat);
        # path from real JID localpart (alice@atl.chat → /avatar/alice). User domain irrelevant.
        avatar_url: str | None = None
        if muc and nick:
            real_jid = muc.get_jid_property(room_jid, nick, "jid")
            if real_jid:
                room_domain = JID(room_jid).domain
                base_domain = room_domain[4:] if room_domain.startswith("muc.") else room_domain
                node = JID(str(real_jid)).local
                avatar_url = f"https://{base_domain}/avatar/{node}"

        _, evt = message_in(
            origin="xmpp",
            channel_id=room_jid,
            author_id=nick,
            author_display=nick,
            content=body,
            message_id=xmpp_msg_id,
            is_edit=is_edit,
            is_action=False,
            avatar_url=avatar_url,
            raw=raw_data if raw_data else {},
        )
        logger.info("XMPP message bridged: room={} author={}", room_jid, nick)
        self._bus.publish("xmpp", evt)

    def _on_reactions(self, msg: Any) -> None:
        """Handle XMPP reactions; emit to bus."""
        from_jid = str(msg["from"]) if msg["from"] else ""
        if "/" in from_jid:
            room_jid = from_jid.split("/")[0]
            nick = from_jid.split("/")[1]
        else:
            return

        mapping = self._router.get_mapping_for_xmpp(room_jid)
        if not mapping:
            return

        # Skip our own echoed reactions (from puppets) to prevent doubling
        plugin_registry = getattr(self, "plugin", None)
        muc = plugin_registry.get("xep_0045", None) if plugin_registry else None
        if muc and nick:
            real_jid = muc.get_jid_property(room_jid, nick, "jid")
            if real_jid:
                sender_domain = JID(str(real_jid)).domain
                our_domain = JID(self._component_jid).domain if "@" in self._component_jid else self._component_jid
                if sender_domain == our_domain:
                    logger.debug("Skipping XMPP reaction echo from our component ({})", nick)
                    return
        if nick == "atl-bridge":
            return

        reactions = msg.get_plugin("reactions", check=True)
        if not reactions:
            return

        target_msg_id = reactions.get("id")
        if not target_msg_id:
            return

        emojis_raw = reactions.get_values()
        new_set = frozenset(e for e in emojis_raw if e and isinstance(e, str))
        cache_key = (target_msg_id, nick)
        prev_set = self._reactions_by_user.get(cache_key, frozenset())
        self._reactions_by_user[cache_key] = new_set

        discord_id = self._msgid_tracker.get_discord_id(target_msg_id)
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
            self._bus.publish("xmpp", evt)
        for emoji in added:
            _, evt = reaction_in(
                origin="xmpp",
                channel_id=room_jid,
                message_id=discord_id,
                emoji=emoji,
                author_id=nick,
                author_display=nick,
            )
            self._bus.publish("xmpp", evt)

    def _on_retraction(self, msg: Any) -> None:
        """Handle XMPP message retraction; emit to bus."""
        from_jid = str(msg["from"]) if msg["from"] else ""
        if "/" in from_jid:
            room_jid = from_jid.split("/")[0]
            nick = from_jid.split("/")[1]
        else:
            return

        mapping = self._router.get_mapping_for_xmpp(room_jid)
        if not mapping:
            return

        retract = msg.get_plugin("retract", check=True)
        if not retract:
            return

        target_msg_id = retract.get("id")
        logger.debug("Received XMPP retraction from {}: message {}", nick, target_msg_id)

        discord_id = self._msgid_tracker.get_discord_id(target_msg_id)
        if not discord_id:
            logger.debug("No Discord msgid for XMPP retraction {}; skip", target_msg_id)
            return

        from bridge.events import message_delete

        _, evt = message_delete(
            origin="xmpp",
            channel_id=room_jid,
            message_id=discord_id,
        )
        self._bus.publish("xmpp", evt)

    def _on_ibb_stream_start(self, stream: Any) -> None:
        """Handle incoming IBB stream; log for now."""
        logger.info(
            "IBB stream from {}: sid={} block_size={}",
            stream.peer,
            stream.sid,
            stream.block_size,
        )
        # Start async handler for this stream
        task = asyncio.create_task(self._handle_ibb_stream(stream))
        self._ibb_streams[stream.sid] = task

    def _on_ibb_stream_end(self, stream: Any) -> None:
        """Handle IBB stream end."""
        logger.info("IBB stream ended: sid={}", stream.sid)
        if stream.sid in self._ibb_streams:
            self._ibb_streams[stream.sid].cancel()
            del self._ibb_streams[stream.sid]

    async def _handle_ibb_stream(self, stream: Any) -> None:
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
            mapping = self._router.get_mapping_for_xmpp(room_jid)
            if not mapping:
                logger.warning("No mapping for XMPP room {}", room_jid)
                return

            # Upload to Discord
            from bridge.adapters.disc import DiscordAdapter

            for adapter in self._bus._adapters:  # type: ignore[attr-defined]
                if isinstance(adapter, DiscordAdapter):
                    filename = f"xmpp_file_{stream.sid[:8]}.bin"
                    await adapter.upload_file(
                        mapping.discord_channel_id,
                        data,
                        filename,
                    )
                    break

            # Notify IRC (file received, no actual transfer)
            _, evt = message_in(
                origin="xmpp",
                channel_id=mapping.discord_channel_id,
                author_id=nick,
                author_display=nick,
                content=f"📎 [File received via XMPP: {len(data)} bytes]",
                message_id=f"xmpp:ibb:{stream.sid}",
                is_action=False,
            )
            self._bus.publish("xmpp", evt)

        except TimeoutError:
            logger.warning("IBB stream timeout: sid={}", stream.sid)
        except Exception as exc:
            logger.exception("IBB stream error: {}", exc)
        finally:
            if stream.sid in self._ibb_streams:
                del self._ibb_streams[stream.sid]

    async def send_file_as_user(self, discord_id: str, peer_jid: str, data: bytes, nick: str) -> None:
        """Send file via IBB stream from a specific Discord user's JID."""
        escaped_nick = _escape_jid_node(nick)
        user_jid = f"{escaped_nick}@{self._component_jid}"
        await self._ensure_puppet_joined(peer_jid, user_jid, nick)

        ibb = self.plugin.get("xep_0047", None)
        if not ibb:
            logger.error("XEP-0047 plugin not available")
            return

        try:
            stream = await ibb.open_stream(  # type: ignore[misc]
                JID(peer_jid),
                ifrom=JID(user_jid),
            )
            await stream.sendall(data)
            await stream.close()
            logger.info(
                "Sent {} bytes via IBB from {} to {}",
                len(data),
                user_jid,
                peer_jid,
            )
        except Exception as exc:
            logger.exception("Failed to send IBB stream: {}", exc)

    async def send_file_url_as_user(self, discord_id: str, muc_jid: str, data: bytes, filename: str, nick: str) -> None:
        """Upload file via HTTP (XEP-0363) and send URL to MUC as user."""
        http_upload = self.plugin.get("xep_0363", None)
        if not http_upload:
            logger.error("XEP-0363 plugin not available")
            return

        try:
            import io
            from pathlib import Path

            url = await http_upload.upload_file(  # type: ignore[misc]
                filename=Path(filename),
                size=len(data),
                input_file=io.BytesIO(data),
            )
            logger.info("Uploaded {} bytes to {}", len(data), url)

            # Send URL as message from user
            await self.send_message_as_user(discord_id, muc_jid, url, nick)
        except Exception as exc:
            logger.exception("Failed to upload file via HTTP: {}", exc)

    async def send_file_with_fallback(
        self, discord_id: str, muc_jid: str, data: bytes, filename: str, nick: str
    ) -> None:
        """Try HTTP upload first, fall back to IBB if it fails."""
        try:
            await self.send_file_url_as_user(discord_id, muc_jid, data, filename, nick)
        except Exception as exc:
            logger.warning("HTTP upload failed, falling back to IBB: {}", exc)
            await self.send_file_as_user(discord_id, muc_jid, data, nick)

    async def send_message_as_user(
        self,
        discord_id: str,
        muc_jid: str,
        content: str,
        nick: str,
        xmpp_msg_id: str | None = None,
        reply_to_id: str | None = None,
        *,
        discord_message_id: str | None = None,
    ) -> str:
        """Send message to MUC from a specific Discord user's JID. Returns XMPP message ID.

        When discord_message_id is provided, stores (xmpp_id, discord_message_id, muc_jid)
        before sending so stanza-id from MUC echo can update the mapping (Discord→XMPP edits).
        """
        escaped_nick = _escape_jid_node(nick)
        user_jid = f"{escaped_nick}@{self._component_jid}"
        # Record before send for echo detection fallback (when get_jid_property returns None)
        self._recent_sent_nicks[(muc_jid, nick)] = None
        await self._ensure_puppet_joined(muc_jid, user_jid, nick)

        try:
            # Convert Discord spoilers ||text|| to XMPP format
            has_spoiler = "||" in content
            if has_spoiler:
                content = content.replace("||", "")

            msg = self.make_message(
                mto=JID(muc_jid),
                mfrom=JID(user_jid),
                mbody=content[:4000],
                mtype="groupchat",
            )
            # Use provided ID or generate one (required for edit tracking)
            if xmpp_msg_id:
                msg["id"] = xmpp_msg_id
            elif not msg.get("id"):
                msg["id"] = f"bridge-{int(time.time() * 1000)}-{uuid.uuid4().hex[:12]}"

            msg_id = msg["id"]
            if discord_message_id:
                self._msgid_tracker.store(msg_id, discord_message_id, muc_jid)

            # Add spoiler tag if Discord message had spoilers
            if has_spoiler:
                msg.enable("spoiler")

            # Add reply reference if replying to another message
            if reply_to_id:
                # Use XEP-0461 (newer, simpler)
                try:
                    reply = msg.enable("reply")
                    reply["to"] = JID(muc_jid)
                    reply["id"] = reply_to_id
                except Exception:
                    pass  # Reply plugin may not be available

                # Also add XEP-0372 reference for compatibility
                try:
                    ref = msg.enable("reference")
                    ref["type"] = "reply"
                    ref["uri"] = f"xmpp:{muc_jid}?id={reply_to_id}"
                except Exception:
                    pass  # Reference plugin may not be available

            # Add origin-id (XEP-0359) so MUC preserves it; we use it to capture stanza-id from echo
            if msg_id:
                try:
                    msg.enable("origin_id")
                    msg["origin_id"]["id"] = str(msg_id)
                except Exception:
                    pass

            msg.send()

            logger.debug("Sent XMPP message {} from {} to {}", msg_id, user_jid, muc_jid)
            return msg_id
        except Exception as exc:
            logger.exception("Failed to send XMPP message as {}: {}", user_jid, exc)
            return ""

    async def send_reaction_as_user(
        self,
        discord_id: str,
        muc_jid: str,
        target_msg_id: str,
        emoji: str,
        nick: str,
        *,
        is_remove: bool = False,
    ) -> None:
        """Send reaction (add or remove) to a message from a specific Discord user's JID."""
        escaped_nick = _escape_jid_node(nick)
        user_jid = f"{escaped_nick}@{self._component_jid}"
        await self._ensure_puppet_joined(muc_jid, user_jid, nick)

        reactions_plugin = self.plugin.get("xep_0444", None)
        if not reactions_plugin:
            logger.error("XEP-0444 plugin not available")
            return

        try:
            # XEP-0444: empty set = remove all reactions from this user
            emoji_set = set() if is_remove else {emoji}
            msg = self.make_message(
                mto=JID(muc_jid),
                mfrom=JID(user_jid),
                mtype="groupchat",
            )
            reactions_plugin.set_reactions(msg, target_msg_id, emoji_set)
            msg.enable("store")
            msg.send()
            logger.info(
                "Sent XMPP reaction %s from %s to msg %s in %s",
                "removal" if is_remove else emoji,
                user_jid,
                target_msg_id,
                muc_jid,
            )
        except Exception as exc:
            logger.exception("Failed to send reaction: {}", exc)

    async def send_retraction_as_user(self, discord_id: str, muc_jid: str, target_msg_id: str, nick: str) -> None:
        """Send message retraction from a specific Discord user's JID."""
        escaped_nick = _escape_jid_node(nick)
        user_jid = f"{escaped_nick}@{self._component_jid}"
        await self._ensure_puppet_joined(muc_jid, user_jid, nick)

        retraction_plugin = self.plugin.get("xep_0424", None)
        if not retraction_plugin:
            logger.error("XEP-0424 plugin not available")
            return

        try:
            await retraction_plugin.send_retraction(  # type: ignore[misc]
                JID(muc_jid),
                target_msg_id,
                mtype="groupchat",
                mfrom=JID(user_jid),
            )
            logger.debug("Sent retraction from {} for message {}", user_jid, target_msg_id)
        except Exception as exc:
            logger.exception("Failed to send retraction: {}", exc)

    async def send_correction_as_user(
        self, discord_id: str, muc_jid: str, content: str, nick: str, original_xmpp_id: str
    ) -> None:
        """Send message correction (XEP-0308) to MUC via slixmpp's build_correction."""
        escaped_nick = _escape_jid_node(nick)
        user_jid = f"{escaped_nick}@{self._component_jid}"
        self._recent_sent_nicks[(muc_jid, nick)] = None
        await self._ensure_puppet_joined(muc_jid, user_jid, nick)

        try:
            xep_0308 = self.plugin.get("xep_0308", None)
            if xep_0308:
                msg = xep_0308.build_correction(
                    id_to_replace=original_xmpp_id,
                    mto=JID(muc_jid),
                    mfrom=JID(user_jid),
                    mtype="groupchat",
                    mbody=content[:4000],
                )
            else:
                msg = self.make_message(
                    mto=JID(muc_jid),
                    mfrom=JID(user_jid),
                    mbody=content[:4000],
                    mtype="groupchat",
                )
                msg.enable("replace")
                msg["replace"]["id"] = original_xmpp_id
            msg.send()
            logger.debug(
                "Sent XMPP correction: replace_id={} from={} to={} body_len={}",
                original_xmpp_id,
                user_jid,
                muc_jid,
                len(content),
            )
        except Exception as exc:
            logger.exception("Failed to send XMPP correction as {}: {}", user_jid, exc)

    async def _ensure_puppet_joined(self, muc_jid: str, user_jid: str, nick: str) -> None:
        """Join MUC as puppet if not already joined (required before sending)."""
        key = (muc_jid, user_jid)
        if key in self._puppets_joined:
            return
        await self.join_muc_as_user(muc_jid, nick)
        self._puppets_joined.add(key)

    async def join_muc_as_user(self, muc_jid: str, nick: str) -> None:
        """Join MUC as a specific user JID. Retries with nick_bridge if primary nick conflicts."""
        escaped_nick = _escape_jid_node(nick)
        user_jid = f"{escaped_nick}@{self._component_jid}"

        muc_plugin = self.plugin.get("xep_0045", None)
        if not muc_plugin:
            logger.error("XEP-0045 plugin not available")
            return

        for attempt, join_nick in enumerate([nick, f"{nick}_bridge"]):
            try:
                await muc_plugin.join_muc_wait(  # type: ignore[misc,call-arg]
                    JID(muc_jid),
                    join_nick,
                    presence_options={"pfrom": JID(user_jid)},
                    timeout=30,
                    maxchars=0,
                )
                if attempt > 0:
                    logger.info("Joined MUC {} as {} (fallback nick, primary '{}' conflicted)", muc_jid, user_jid, nick)
                else:
                    logger.info("Joined MUC {} as {}", muc_jid, user_jid)
                return
            except TimeoutError as exc:
                if attempt == 0:
                    logger.warning(
                        "Join MUC {} as {} (nick '{}') timed out; retrying with '{}_bridge'",
                        muc_jid,
                        user_jid,
                        nick,
                        nick,
                    )
                else:
                    logger.exception("Join MUC {} as {} failed after retry: {}", muc_jid, user_jid, exc)
                    return  # Don't raise; caller continues without this puppet
            except XMPPError as exc:
                if attempt == 0:
                    logger.warning(
                        "Join MUC {} as {} failed: {}; retrying with '{}_bridge'", muc_jid, user_jid, exc, nick
                    )
                else:
                    logger.warning("Failed to join MUC {} as {}: {}", muc_jid, user_jid, exc)
                    return  # Don't raise; preserve original behavior (log only)

    async def _fetch_avatar_bytes(self, avatar_url: str) -> bytes | None:
        """Download avatar image from URL."""
        if not self._session:
            return None
        try:
            async with self._session.get(avatar_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.read()
                logger.warning("Failed to fetch avatar from {}: status {}", avatar_url, resp.status)
        except Exception as exc:
            logger.exception("Error fetching avatar from {}: {}", avatar_url, exc)
        return None

    async def set_avatar_for_user(self, discord_id: str, nick: str, avatar_url: str | None) -> None:
        """Set vCard avatar for Discord user's puppet JID."""
        if not avatar_url:
            return

        escaped_nick = _escape_jid_node(nick)
        user_jid = f"{escaped_nick}@{self._component_jid}"

        # Download avatar
        avatar_bytes = await self._fetch_avatar_bytes(avatar_url)
        if not avatar_bytes:
            return

        # Check if avatar changed
        avatar_hash = hashlib.sha1(avatar_bytes).hexdigest()
        if self._avatar_cache.get(discord_id) == avatar_hash:
            return  # Avatar unchanged

        # Set vCard photo directly via XEP-0054
        vcard_plugin = self.plugin.get("xep_0054", None)
        if not vcard_plugin:
            logger.error("XEP-0054 plugin not available")
            return

        try:
            vcard = vcard_plugin.make_vcard()  # type: ignore[misc]
            vcard["PHOTO"]["TYPE"] = "image/png"
            vcard["PHOTO"]["BINVAL"] = avatar_bytes

            await vcard_plugin.publish_vcard(  # type: ignore[misc]
                jid=JID(user_jid),
                vcard=vcard,
            )

            self._avatar_cache[discord_id] = avatar_hash
            logger.debug("Set avatar for {} (hash: {})", user_jid, avatar_hash[:8])
        except Exception as exc:
            logger.exception("Failed to set avatar for {}: {}", user_jid, exc)
