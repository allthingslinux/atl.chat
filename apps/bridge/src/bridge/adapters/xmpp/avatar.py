"""XMPP avatar management — PEP and vCard avatar handling.

All functions receive the component instance as the first parameter.
"""

from __future__ import annotations

import base64
import hashlib
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

import aiohttp
from loguru import logger
from slixmpp import JID

from bridge.adapters.xmpp.component import _escape_jid_node

if TYPE_CHECKING:
    from bridge.adapters.xmpp.component import XMPPComponent


def _decode_data_url(url: str) -> bytes | None:
    """Decode data: URL (e.g. from Portal user.image) to bytes."""
    if not url.strip().lower().startswith("data:"):
        return None
    try:
        # data:image/png;base64,<payload>
        parts = url.split(",", 1)
        if len(parts) != 2:
            return None
        payload = parts[1]
        return base64.b64decode(payload)
    except Exception:
        return None


def resolve_avatar_url(comp: XMPPComponent, base_domain: str, node: str) -> str | None:
    """Resolve avatar URL: try /pep_avatar/ first, then /avatar/ (vCard) as fallback. Cached."""
    from bridge.avatar import resolve_xmpp_avatar_url

    return resolve_xmpp_avatar_url(base_domain, node)


async def fetch_avatar_bytes(comp: XMPPComponent, avatar_url: str) -> bytes | None:
    """Download avatar image from URL, or decode data: URL (e.g. Portal base64)."""
    decoded = _decode_data_url(avatar_url)
    if decoded is not None:
        return decoded
    if not comp._session:
        return None
    try:
        async with comp._session.get(avatar_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                return await resp.read()
            logger.warning("Failed to fetch avatar from {}: status {}", avatar_url[:80], resp.status)
    except Exception as exc:
        logger.exception("Error fetching avatar from {}: {}", avatar_url[:80], exc)
    return None


async def set_avatar_for_user(
    comp: XMPPComponent,
    discord_id: str,
    nick: str,
    avatar_url: str | None,
) -> str | None:
    """Set vCard avatar for Discord user's puppet JID.

    Returns the avatar SHA-1 hash (from cache or freshly published) so the
    caller can broadcast it via ``broadcast_avatar_presence`` *after* the
    puppet has joined the target MUC(s).  Returns ``None`` only when there
    is no avatar to set.
    """
    if not avatar_url:
        logger.debug("set_avatar_for_user: no avatar_url for {}", nick)
        return None

    escaped_nick = _escape_jid_node(nick)
    user_jid = f"{escaped_nick}@{comp._component_jid}"

    # Download avatar (call through comp's delegation stub so tests can mock it)
    avatar_bytes = await comp._fetch_avatar_bytes(avatar_url)
    if not avatar_bytes:
        logger.info("Avatar download failed for {} (url: {})", nick, avatar_url[:80])
        return None

    # Check if avatar changed
    avatar_hash = hashlib.sha1(avatar_bytes).hexdigest()
    if comp._avatar_cache.get(discord_id) == avatar_hash:
        return avatar_hash

    # Set vCard photo directly via XEP-0054
    vcard_plugin = comp.plugin.get("xep_0054", None)
    if not vcard_plugin:
        logger.error("XEP-0054 plugin not available")
        return None

    try:
        vcard = vcard_plugin.make_vcard()  # type: ignore[misc]
        vcard["PHOTO"]["TYPE"] = "image/png"
        vcard["PHOTO"]["BINVAL"] = avatar_bytes

        await vcard_plugin.publish_vcard(  # type: ignore[misc]
            jid=JID(user_jid),
            vcard=vcard,
        )

        comp._avatar_cache[discord_id] = avatar_hash
        # Avatar changed — clear broadcast tracker so all MUCs get the new hash
        comp._avatar_broadcast_done = {k for k in comp._avatar_broadcast_done if k[1] != user_jid}
        logger.info("Set vCard avatar for {} (hash: {})", user_jid, avatar_hash[:8])
        return avatar_hash
    except Exception as exc:
        logger.exception("Failed to set avatar for {}: {}", user_jid, exc)
        return None


async def broadcast_avatar_presence(
    comp: XMPPComponent,
    user_jid: str,
    avatar_hash: str,
) -> None:
    """Send updated presence with XEP-0153 vCard avatar hash to all MUCs the puppet is in."""
    matched = False
    for muc_jid, joined_jid in list(comp._puppets_joined):
        if joined_jid != user_jid:
            continue
        matched = True
        try:
            # Build nick from user_jid localpart (the escaped nick)
            nick_str = user_jid.split("@", maxsplit=1)[0]

            presence = comp.make_presence(
                pto=JID(f"{muc_jid}/{nick_str}"),
                pfrom=JID(user_jid),
            )
            # Add XEP-0153 vcard-temp:x:update with photo hash
            x_update = ET.SubElement(presence.xml, "{vcard-temp:x:update}x")
            ET.SubElement(x_update, "photo").text = avatar_hash
            presence.send()

            logger.info("Broadcast avatar hash {} to {} for {}", avatar_hash[:8], muc_jid, user_jid)
        except Exception as exc:
            logger.warning("Failed to broadcast avatar presence to {}: {}", muc_jid, exc)
    if not matched:
        logger.warning(
            "No MUC entries in _puppets_joined for {} (total entries: {})",
            user_jid,
            len(comp._puppets_joined),
        )
