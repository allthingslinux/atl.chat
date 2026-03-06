"""XMPP component: per-Discord-user JIDs with ComponentXMPP.

After decomposition (Phase 4), this module contains only:
- Connection and session management
- XEP plugin registration
- MUC joining logic
- Utility functions shared across submodules

Inbound handlers → handlers.py
Outbound sending → outbound.py
Media/file transfer → media.py
Avatar management → avatar.py
"""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any

import aiohttp
from cachetools import TTLCache
from loguru import logger
from slixmpp import JID
from slixmpp.componentxmpp import ComponentXMPP
from slixmpp.exceptions import XMPPError

from bridge.adapters.xmpp.msgid import XMPPMessageIDTracker
from bridge.gateway import Bus, ChannelRouter

# ---------------------------------------------------------------------------
# XEP-0106 JID escape map: chars disallowed by nodeprep -> escape sequence.
# slixmpp's XEP_0106 plugin only advertises disco; it has no escape API.
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Shared constants used by submodules
# ---------------------------------------------------------------------------

SID_NS = "urn:xmpp:sid:0"

# Bare URL pattern: body is *only* a URL (no other text)
_BARE_URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)

# Content-Type → file extension for image re-upload
_CT_TO_EXT: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/avif": ".avif",
    "image/bmp": ".bmp",
}

# Extensions already recognised as media by XMPP clients
_MEDIA_EXTENSIONS = frozenset(
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".mp4",
        ".webm",
        ".svg",
        ".avif",
        ".bmp",
    }
)


def _url_has_media_extension(url: str) -> bool:
    """Return True when the URL path (before query/fragment) ends with a known media extension."""
    path = url.split("?", 1)[0].split("#", 1)[0]
    dot = path.rfind(".")
    if dot == -1:
        return False
    ext = path[dot:].lower()
    return ext in _MEDIA_EXTENSIONS


def _capture_stanza_id_from_echo(tracker: XMPPMessageIDTracker, msg: Any, room_jid: str) -> None:
    """Capture IDs from our echo for correction and reaction mapping.

    XMPP MUC servers (Prosody) may assign a stanza-id that differs from the
    origin-id we sent. The distinction matters:

    - Corrections (XEP-0308): Gajim uses the top-level msg id (our origin-id)
      for ``<replace id="..."/>``, so we keep origin-id as the primary key.
    - Reactions (XEP-0444 §4.2): MUC requires stanza-id (assigned by server),
      so we add it as an alias for reaction lookups.

    We only replace origin-id with stanza-id when the server rewrote the
    top-level msg.id to match stanza-id, indicating the server replaced our
    id entirely for delivery.
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
    """XMPP component for multi-presence bridge (puppets).

    After decomposition this class is the connection/session orchestrator.
    Handler, outbound, media, and avatar logic live in their own modules
    and receive ``self`` as the first parameter.
    """

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
        self._server = server
        self._avatar_cache: TTLCache[str, str] = TTLCache(
            maxsize=1000, ttl=86400
        )  # discord_id -> avatar_hash (24h TTL)
        self._session: aiohttp.ClientSession | None = None
        self._ibb_streams: dict[str, asyncio.Task] = {}  # sid -> handler task
        self._msgid_tracker = XMPPMessageIDTracker()  # Track message IDs for edits
        self._puppets_joined: set[tuple[str, str]] = set()  # (muc_jid, user_jid) — avoid re-join
        # Track which (muc_jid, user_jid) pairs have had their avatar hash broadcast
        # so we don't re-broadcast on every message.  Cleared when avatar changes.
        self._avatar_broadcast_done: set[tuple[str, str]] = set()
        # Dedupe: MUC delivers same message to each occupant (listener + puppets) — process once
        self._seen_msg_ids: TTLCache[tuple[str, str], None] = TTLCache(maxsize=500, ttl=60)
        # Fallback echo detection when get_jid_property returns None (MUC may not expose real JID)
        self._recent_sent_nicks: TTLCache[tuple[str, str], None] = TTLCache(maxsize=200, ttl=10)
        # XEP-0444: track per-user reaction sets to detect removals (full set sent each update)
        self._reactions_by_user: TTLCache[tuple[str, str], frozenset[str]] = TTLCache(maxsize=2000, ttl=3600)
        # Dedupe moderation: MUC delivers to each occupant + multiple handlers fire per stanza
        self._seen_moderation_ids: TTLCache[str, None] = TTLCache(maxsize=200, ttl=60)
        # Dedupe retractions: MUC echo + multiple occupant copies
        self._seen_retraction_ids: TTLCache[str, None] = TTLCache(maxsize=200, ttl=60)
        # MUC status code handling (Requirement 26)
        self._banned_rooms: set[str] = set()  # MUC JIDs we've been banned from (status 301)
        self._auto_rejoin: bool = True  # Whether to auto-rejoin after kick/removal
        self._confirmed_mucs: set[str] = set()  # MUC JIDs confirmed joined (status 110)

        # -------------------------------------------------------------------
        # XEP Registration (Requirement 10.6)
        # Plugins are registered in dependency order. Some XEPs depend on
        # others (e.g. XEP-0425 depends on XEP-0421), and slixmpp handles
        # this internally, but we list them in logical groups for clarity.
        # -------------------------------------------------------------------
        self.register_plugin("xep_0030")  # Service Discovery (foundation for all XEP negotiation)
        self.register_plugin(
            "xep_0045", {"multi_from": True}
        )  # MUC: multi_from enables per-user JIDs (component simulates multiple entities)
        self.register_plugin("xep_0198")  # Stream Management
        self.register_plugin("xep_0199")  # XMPP Ping
        self.register_plugin("xep_0203")  # Delayed Delivery
        self.register_plugin("xep_0308")  # Last Message Correction
        self.register_plugin("xep_0359")  # Unique Stanza IDs (origin-id for echo capture)
        self.register_plugin("xep_0054")  # vCard-temp
        self.register_plugin("xep_0047")  # In-Band Bytestreams
        self.register_plugin("xep_0066")  # Out of Band Data (file URLs in messages)
        self.register_plugin("xep_0363")  # HTTP File Upload
        self.register_plugin("xep_0372")  # References
        self.register_plugin("xep_0382")  # Spoiler Messages
        self.register_plugin("xep_0422")  # Message Fastening
        self.register_plugin("xep_0424")  # Message Retraction
        self.register_plugin("xep_0421")  # Anonymous unique occupant identifiers (dep of 0425)
        self.register_plugin("xep_0425")  # Message Moderation (moderator retraction)
        self.register_plugin("xep_0444")  # Message Reactions
        self.register_plugin("xep_0461")  # Message Replies
        self.register_plugin("xep_0106")  # JID Escaping
        self.register_plugin("xep_0394")  # Message Markup (bold/italic/code spans)
        self.register_plugin("xep_0334")  # Message Processing Hints (no-store for reactions/typing)
        self.register_plugin("xep_0428")  # Fallback Indication (reply fallback bodies)

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
                name="Bridge",
            )

        # -------------------------------------------------------------------
        # Event handler registration — delegates to extracted modules
        # -------------------------------------------------------------------
        self.add_event_handler("groupchat_message", self._on_groupchat_message)
        self.add_event_handler("reactions", self._on_reactions)
        self.add_event_handler("message_retract", self._on_retraction)
        self.add_event_handler("moderated_message", self._on_moderated_message)
        self.add_event_handler("ibb_stream_start", self._on_ibb_stream_start)
        self.add_event_handler("ibb_stream_end", self._on_ibb_stream_end)
        self.add_event_handler("session_start", self._on_session_start)
        self.add_event_handler("disconnected", self._on_disconnected)
        self.add_event_handler(f"muc::{'*'}::got_online", self._on_muc_presence)
        self.add_event_handler(f"muc::{'*'}::got_offline", self._on_muc_presence)

        # XEP-0425 moderation: Prosody sends moderation announcements as
        # <message type="groupchat" from="room@muc"> with <apply-to> (v0)
        # and <retract><moderated> (v1) but NO <body>.  slixmpp's MUC handler
        # requires <body/> so groupchat_message never fires, and the XEP-0424
        # handler may not match due to component namespace rewriting.
        # We register a raw handler that catches ALL groupchat messages to
        # intercept these bodyless moderation announcements that would
        # otherwise be silently dropped.
        from slixmpp.xmlstream.handler import Callback as _Callback
        from slixmpp.xmlstream.matcher import MatchXMLMask as _MatchXMLMask

        self.register_handler(
            _Callback(
                "MUCModeration",
                _MatchXMLMask(f"<message xmlns='{self.default_ns}' type='groupchat'/>"),
                self._on_raw_groupchat,
            )
        )

        logger.debug(
            "MUCModeration handler registered (default_ns={})",
            self.default_ns,
        )

    # ===================================================================
    # Connection & session management (kept in component.py)
    # ===================================================================

    async def _on_session_start(self, event: Any) -> None:
        """Initialize HTTP session and join MUCs for receiving messages."""
        if not self._session:
            self._session = aiohttp.ClientSession()

        # Join all mapped MUCs so we receive groupchat_message events (XMPP → Discord/IRC)
        muc_plugin = self.plugin.get("xep_0045", None)
        if muc_plugin:
            bridge_nick = "bridge"
            bridge_jid = f"bridge@{self._component_jid}"
            for mapping in self._router.all_mappings():
                if mapping.xmpp:
                    try:
                        await muc_plugin.join_muc_wait(  # type: ignore[misc,call-arg]
                            JID(mapping.xmpp.muc_jid),
                            bridge_nick,
                            presence_options={"pfrom": JID(bridge_jid)},
                            timeout=30,
                            maxchars=0,  # Requirement 10.11 / 18.1: suppress MUC history replay
                        )
                        logger.info("Joined MUC {} as listener ({})", mapping.xmpp.muc_jid, bridge_nick)
                    except XMPPError as exc:
                        logger.warning("Failed to join MUC {}: {}", mapping.xmpp.muc_jid, exc)

    async def _on_disconnected(self, event: Any) -> None:
        """Clean up state on XMPP disconnect so reconnect starts fresh."""
        # Clear puppet join tracking — MUC evicts all occupants on disconnect,
        # so _ensure_puppet_joined must re-join them after reconnect.
        self._puppets_joined.clear()
        self._avatar_broadcast_done.clear()
        self._confirmed_mucs.clear()
        if self._session:
            await self._session.close()
            self._session = None

    # ===================================================================
    # MUC joining (kept in component.py)
    # ===================================================================

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
                    maxchars=0,  # Requirement 10.11 / 18.1: suppress MUC history replay
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

    # ===================================================================
    # Thin delegation stubs — backward compatibility for existing callers
    # ===================================================================

    # --- Inbound handlers (delegate to handlers.py) ---

    def _on_groupchat_message(self, msg: Any) -> None:
        from bridge.adapters.xmpp.handlers import on_groupchat_message

        on_groupchat_message(self, msg)

    def _on_reactions(self, msg: Any) -> None:
        from bridge.adapters.xmpp.handlers import on_reactions

        on_reactions(self, msg)

    def _on_retraction(self, msg: Any) -> None:
        from bridge.adapters.xmpp.handlers import on_retraction

        on_retraction(self, msg)

    def _on_moderated_message(self, msg: Any) -> None:
        from bridge.adapters.xmpp.handlers import on_moderated_message

        on_moderated_message(self, msg)

    def _try_handle_moderation(self, msg: Any, room_jid: str) -> None:
        from bridge.adapters.xmpp.handlers import try_handle_moderation

        try_handle_moderation(self, msg, room_jid)

    def _on_raw_groupchat(self, msg: Any) -> None:
        from bridge.adapters.xmpp.handlers import on_raw_groupchat

        on_raw_groupchat(self, msg)

    def _on_ibb_stream_start(self, stream: Any) -> None:
        from bridge.adapters.xmpp.handlers import on_ibb_stream_start

        on_ibb_stream_start(self, stream)

    def _on_ibb_stream_end(self, stream: Any) -> None:
        from bridge.adapters.xmpp.handlers import on_ibb_stream_end

        on_ibb_stream_end(self, stream)

    def _on_muc_presence(self, presence: Any) -> None:
        from bridge.adapters.xmpp.handlers import on_muc_presence

        on_muc_presence(self, presence)

    async def _handle_ibb_stream(self, stream: Any) -> None:
        from bridge.adapters.xmpp.handlers import handle_ibb_stream

        await handle_ibb_stream(self, stream)

    # --- Outbound sending (delegate to outbound.py) ---

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
        is_media: bool = False,
        markup_spans: list | None = None,
        media_width: int | None = None,
        media_height: int | None = None,
    ) -> str:
        from bridge.adapters.xmpp.outbound import send_message_as_user

        return await send_message_as_user(
            self,
            discord_id,
            muc_jid,
            content,
            nick,
            xmpp_msg_id,
            reply_to_id,
            discord_message_id=discord_message_id,
            is_media=is_media,
            markup_spans=markup_spans,
            media_width=media_width,
            media_height=media_height,
        )

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
        from bridge.adapters.xmpp.outbound import send_reaction_as_user

        await send_reaction_as_user(self, discord_id, muc_jid, target_msg_id, emoji, nick, is_remove=is_remove)

    async def send_retraction_as_user(self, discord_id: str, muc_jid: str, target_msg_id: str, nick: str) -> None:
        from bridge.adapters.xmpp.outbound import send_retraction_as_user

        await send_retraction_as_user(self, discord_id, muc_jid, target_msg_id, nick)

    async def send_retraction_as_bridge(self, muc_jid: str, target_msg_id: str) -> None:
        from bridge.adapters.xmpp.outbound import send_retraction_as_bridge

        await send_retraction_as_bridge(self, muc_jid, target_msg_id)

    async def send_correction_as_user(
        self, discord_id: str, muc_jid: str, content: str, nick: str, original_xmpp_id: str
    ) -> None:
        from bridge.adapters.xmpp.outbound import send_correction_as_user

        await send_correction_as_user(self, discord_id, muc_jid, content, nick, original_xmpp_id)

    # --- Media (delegate to media.py) ---

    async def send_file_as_user(self, discord_id: str, peer_jid: str, data: bytes, nick: str) -> None:
        from bridge.adapters.xmpp.media import send_file_as_user

        await send_file_as_user(self, discord_id, peer_jid, data, nick)

    async def send_file_url_as_user(self, discord_id: str, muc_jid: str, data: bytes, filename: str, nick: str) -> None:
        from bridge.adapters.xmpp.media import send_file_url_as_user

        await send_file_url_as_user(self, discord_id, muc_jid, data, filename, nick)

    async def send_file_with_fallback(
        self, discord_id: str, muc_jid: str, data: bytes, filename: str, nick: str
    ) -> None:
        from bridge.adapters.xmpp.media import send_file_with_fallback

        await send_file_with_fallback(self, discord_id, muc_jid, data, filename, nick)

    async def reupload_extensionless_image(self, url: str) -> str | None:
        from bridge.adapters.xmpp.media import reupload_extensionless_image

        return await reupload_extensionless_image(self, url)

    # --- Avatar (delegate to avatar.py) ---

    def _resolve_avatar_url(self, base_domain: str, node: str) -> str | None:
        from bridge.adapters.xmpp.avatar import resolve_avatar_url

        return resolve_avatar_url(self, base_domain, node)

    async def _fetch_avatar_bytes(self, avatar_url: str) -> bytes | None:
        from bridge.adapters.xmpp.avatar import fetch_avatar_bytes

        return await fetch_avatar_bytes(self, avatar_url)

    async def set_avatar_for_user(self, discord_id: str, nick: str, avatar_url: str | None) -> str | None:
        from bridge.adapters.xmpp.avatar import set_avatar_for_user

        return await set_avatar_for_user(self, discord_id, nick, avatar_url)

    async def _broadcast_avatar_presence(self, user_jid: str, avatar_hash: str) -> None:
        from bridge.adapters.xmpp.avatar import broadcast_avatar_presence

        await broadcast_avatar_presence(self, user_jid, avatar_hash)
