"""XMPP media handling — HTTP Upload, IBB file transfer, image re-upload.

All functions receive the component instance as the first parameter.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING

import aiohttp
from loguru import logger
from slixmpp import JID

from bridge.adapters.xmpp.component import (
    _CT_TO_EXT,
    _escape_jid_node,
    _url_has_media_extension,
)

if TYPE_CHECKING:
    from bridge.adapters.xmpp.component import XMPPComponent


async def send_file_as_user(
    comp: XMPPComponent,
    discord_id: str,
    peer_jid: str,
    data: bytes,
    nick: str,
) -> None:
    """Send file via IBB stream from a specific Discord user's JID."""
    escaped_nick = _escape_jid_node(nick)
    user_jid = f"{escaped_nick}@{comp._component_jid}"
    await comp._ensure_puppet_joined(peer_jid, user_jid, nick)

    ibb = comp.plugin.get("xep_0047", None)
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
    comp: XMPPComponent,
    discord_id: str,
    muc_jid: str,
    data: bytes,
    filename: str,
    nick: str,
) -> None:
    """Upload file via HTTP (XEP-0363) and send URL to MUC as user."""
    http_upload = comp.plugin.get("xep_0363", None)
    if not http_upload:
        logger.error("XEP-0363 plugin not available")
        return

    try:
        url = await http_upload.upload_file(  # type: ignore[misc]
            filename=Path(filename),
            size=len(data),
            input_file=io.BytesIO(data),
            domain=comp._server,
        )
        logger.info("Uploaded {} bytes to {}", len(data), url)

        # Send URL as message from user
        await comp.send_message_as_user(discord_id, muc_jid, url, nick, is_media=True)
    except Exception as exc:
        logger.exception("Failed to upload file via HTTP: {}", exc)


async def send_file_with_fallback(
    comp: XMPPComponent,
    discord_id: str,
    muc_jid: str,
    data: bytes,
    filename: str,
    nick: str,
) -> None:
    """Try HTTP upload first, fall back to IBB if it fails."""
    try:
        # Call through the component's delegation stubs so tests can mock them
        await comp.send_file_url_as_user(discord_id, muc_jid, data, filename, nick)
    except Exception as exc:
        logger.warning("HTTP upload failed, falling back to IBB: {}", exc)
        await comp.send_file_as_user(discord_id, muc_jid, data, nick)


async def reupload_extensionless_image(comp: XMPPComponent, url: str) -> str | None:
    """Re-upload an image URL that lacks a file extension.

    XMPP clients (Gajim, Dino) determine file type from the URL path, not
    Content-Type headers. URLs like ``https://avatars.githubusercontent.com/u/123?s=200``
    have no extension, so they render as generic file attachments instead of
    inline images.

    This method:
    1. Checks the URL path for an existing media extension (skip if found).
    2. HEAD-probes to check Content-Type.
    3. Downloads the image data (max 10 MB).
    4. Re-uploads via XEP-0363 HTTP Upload with a proper filename extension.

    Returns the new upload URL (with a proper extension) or None.
    """
    if _url_has_media_extension(url):
        return None  # Already has extension; no action needed

    if not comp._session:
        return None

    # HEAD probe to determine Content-Type
    try:
        async with comp._session.head(
            url,
            timeout=aiohttp.ClientTimeout(total=5),
            allow_redirects=True,
        ) as resp:
            if resp.status != 200:
                return None
            ct = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
            ext = _CT_TO_EXT.get(ct)
            if not ext:
                return None  # Not a recognised image type
    except Exception as exc:
        logger.debug("Image re-upload: HEAD probe failed for {}: {}", url, exc)
        return None

    # Download image data
    try:
        async with comp._session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.read()
            if len(data) > 10 * 1024 * 1024:
                return None
    except Exception as exc:
        logger.debug("Image re-upload: download failed for {}: {}", url, exc)
        return None

    # Re-upload via XEP-0363 HTTP Upload
    http_upload = comp.plugin.get("xep_0363", None)
    if not http_upload:
        return None

    try:
        filename = f"image{ext}"
        uploaded_url = await http_upload.upload_file(  # type: ignore[misc]
            filename=Path(filename),
            size=len(data),
            input_file=io.BytesIO(data),
            domain=comp._server,
        )
        logger.info("Re-uploaded extensionless image: {} -> {}", url, uploaded_url)
        return str(uploaded_url)
    except Exception as exc:
        logger.debug("Image re-upload: HTTP upload failed: {}", exc)
        return None
