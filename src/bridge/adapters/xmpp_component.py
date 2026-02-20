"""XMPP component: per-Discord-user JIDs with ComponentXMPP."""

from __future__ import annotations

import asyncio
import hashlib
from typing import TYPE_CHECKING, Any

import aiohttp
from loguru import logger
from slixmpp import JID
from slixmpp.componentxmpp import ComponentXMPP
from slixmpp.exceptions import XMPPError

from bridge.adapters.xmpp_msgid import XMPPMessageIDTracker
from bridge.events import message_in
from bridge.gateway import Bus, ChannelRouter

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
        identity: IdentityResolver,
    ):
        ComponentXMPP.__init__(self, jid, secret, server, port)
        self._bus = bus
        self._router = router
        self._identity = identity
        self._component_jid = jid
        self._avatar_cache: dict[str, str] = {}  # discord_id -> avatar_hash
        self._ibb_streams: dict[str, asyncio.Task] = {}  # sid -> handler task
        self._msgid_tracker = XMPPMessageIDTracker()  # Track message IDs for edits

        # Register XEPs
        self.register_plugin("xep_0030")  # Service Discovery
        self.register_plugin("xep_0045")  # Multi-User Chat
        self.register_plugin("xep_0198")  # Stream Management
        self.register_plugin("xep_0199")  # XMPP Ping
        self.register_plugin("xep_0203")  # Delayed Delivery
        self.register_plugin("xep_0308")  # Last Message Correction
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
        disco = self.plugin.get("xep_0030")
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
            return

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

        # Get or generate message ID
        xmpp_msg_id = msg.get("id", f"xmpp:{room_jid}:{nick}:{id(msg)}")

        raw_data = {}
        if replace_id:
            raw_data["replace_id"] = replace_id
        if reply_to_id:
            raw_data["reply_to_id"] = reply_to_id

        _, evt = message_in(
            origin="xmpp",
            channel_id=mapping.discord_channel_id,
            author_id=nick,
            author_display=nick,
            content=body,
            message_id=xmpp_msg_id,
            is_edit=is_edit,
            is_action=False,
            raw=raw_data if raw_data else {},
        )
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

        reactions = msg.get_plugin("reactions", check=True)
        if not reactions:
            return

        target_msg_id = reactions.get("id")
        emojis = reactions.get_values()
        if not target_msg_id or not emojis:
            return

        discord_id = self._msgid_tracker.get_discord_id(target_msg_id)
        if not discord_id:
            logger.debug("No Discord msgid for XMPP reaction on {}; skip", target_msg_id)
            return

        from bridge.events import reaction_in

        for emoji in emojis:
            if emoji and isinstance(emoji, str):
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
                room_jid = peer_str.split("/")[0]
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

        except asyncio.TimeoutError:
            logger.warning("IBB stream timeout: sid={}", stream.sid)
        except Exception as exc:
            logger.exception("IBB stream error: {}", exc)
        finally:
            if stream.sid in self._ibb_streams:
                del self._ibb_streams[stream.sid]

    async def send_file_as_user(
        self, discord_id: str, peer_jid: str, data: bytes, nick: str
    ) -> None:
        """Send file via IBB stream from a specific Discord user's JID."""
        # Escape nick for JID compliance
        jid_escape = self.plugin.get("xep_0106")
        if not jid_escape:
            logger.error("XEP-0106 plugin not available")
            return
        escaped_nick = jid_escape.escape(nick)  # type: ignore[misc]
        user_jid = f"{escaped_nick}@{self._component_jid}"

        ibb = self.plugin.get("xep_0047")
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

    async def send_file_url_as_user(
        self, discord_id: str, muc_jid: str, data: bytes, filename: str, nick: str
    ) -> None:
        """Upload file via HTTP (XEP-0363) and send URL to MUC as user."""
        http_upload = self.plugin.get("xep_0363")
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
    ) -> str:
        """Send message to MUC from a specific Discord user's JID. Returns XMPP message ID."""
        # Escape nick for JID compliance
        jid_escape = self.plugin.get("xep_0106")
        if not jid_escape:
            logger.error("XEP-0106 plugin not available")
            return ""
        escaped_nick = jid_escape.escape(nick)  # type: ignore[misc]
        user_jid = f"{escaped_nick}@{self._component_jid}"

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
            # Use provided ID or generate one
            if xmpp_msg_id:
                msg["id"] = xmpp_msg_id

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

            msg.send()

            msg_id = msg["id"]
            logger.debug("Sent XMPP message {} from {} to {}", msg_id, user_jid, muc_jid)
            return msg_id
        except Exception as exc:
            logger.exception("Failed to send XMPP message as {}: {}", user_jid, exc)
            return ""

    async def send_reaction_as_user(
        self, discord_id: str, muc_jid: str, target_msg_id: str, emoji: str, nick: str
    ) -> None:
        """Send reaction to a message from a specific Discord user's JID."""
        jid_escape = self.plugin.get("xep_0106")
        if not jid_escape:
            logger.error("XEP-0106 plugin not available")
            return
        escaped_nick = jid_escape.escape(nick)  # type: ignore[misc]
        user_jid = f"{escaped_nick}@{self._component_jid}"

        reactions_plugin = self.plugin.get("xep_0444")
        if not reactions_plugin:
            logger.error("XEP-0444 plugin not available")
            return

        try:
            await reactions_plugin.send_reactions(  # type: ignore[misc,call-arg]
                muc_jid,
                target_msg_id,
                {emoji},
                ifrom=user_jid,  # pyright: ignore[reportCallIssue]
            )
            logger.debug("Sent reaction {} from {} to message {}", emoji, user_jid, target_msg_id)
        except Exception as exc:
            logger.exception("Failed to send reaction: {}", exc)

    async def send_retraction_as_user(
        self, discord_id: str, muc_jid: str, target_msg_id: str, nick: str
    ) -> None:
        """Send message retraction from a specific Discord user's JID."""
        jid_escape = self.plugin.get("xep_0106")
        if not jid_escape:
            logger.error("XEP-0106 plugin not available")
            return
        escaped_nick = jid_escape.escape(nick)  # type: ignore[misc]
        user_jid = f"{escaped_nick}@{self._component_jid}"

        retraction_plugin = self.plugin.get("xep_0424")
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
        """Send message correction (XEP-0308) to MUC."""
        # Escape nick for JID compliance
        jid_escape = self.plugin.get("xep_0106")
        if not jid_escape:
            logger.error("XEP-0106 plugin not available")
            return
        escaped_nick = jid_escape.escape(nick)  # type: ignore[misc]
        user_jid = f"{escaped_nick}@{self._component_jid}"

        try:
            msg = self.make_message(
                mto=JID(muc_jid),
                mfrom=JID(user_jid),
                mbody=content[:4000],
                mtype="groupchat",
            )
            msg["replace"]["id"] = original_xmpp_id
            msg.send()
            logger.debug(
                "Sent XMPP correction for {} from {} to {}", original_xmpp_id, user_jid, muc_jid
            )
        except Exception as exc:
            logger.exception("Failed to send XMPP correction as {}: {}", user_jid, exc)

    async def join_muc_as_user(self, muc_jid: str, nick: str) -> None:
        """Join MUC as a specific user JID."""
        # Escape nick for JID compliance
        jid_escape = self.plugin.get("xep_0106")
        if not jid_escape:
            logger.error("XEP-0106 plugin not available")
            return
        escaped_nick = jid_escape.escape(nick)  # type: ignore[misc]
        user_jid = f"{escaped_nick}@{self._component_jid}"

        muc_plugin = self.plugin.get("xep_0045")
        if not muc_plugin:
            logger.error("XEP-0045 plugin not available")
            return

        try:
            await muc_plugin.join_muc_wait(  # type: ignore[misc,call-arg]
                JID(muc_jid),
                nick,
                mfrom=JID(user_jid),
                timeout=30,
                maxchars=0,  # pyright: ignore[reportCallIssue]
            )
            logger.info("Joined MUC {} as {}", muc_jid, user_jid)
        except XMPPError as exc:
            logger.warning("Failed to join MUC {} as {}: {}", muc_jid, user_jid, exc)

    async def _fetch_avatar_bytes(self, avatar_url: str) -> bytes | None:
        """Download avatar image from URL."""
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(avatar_url, timeout=aiohttp.ClientTimeout(total=10)) as resp,
            ):
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

        # Escape nick for JID compliance
        jid_escape = self.plugin.get("xep_0106")
        if not jid_escape:
            logger.error("XEP-0106 plugin not available")
            return
        escaped_nick = jid_escape.escape(nick)  # type: ignore[misc]
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
        vcard_plugin = self.plugin.get("xep_0054")
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
