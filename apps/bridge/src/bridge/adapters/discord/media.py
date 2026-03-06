"""Discord media handling: fetch, probe, upload, URL rewriting (AUDIT §2.B)."""

from __future__ import annotations

import contextlib
import io
import os
import re
import tempfile

import aiohttp
from discord import File, TextChannel
from discord.ext import commands
from loguru import logger

# Media URL pattern: single URL, no surrounding text (discord-ircv3 style).
# Matches URLs whose *path* (before any query string) ends with a media extension.
MEDIA_URL_PATTERN = re.compile(
    r"^https?://[^\s\x01-\x16]+\.(?:jpg|jpeg|png|gif|mp4|webm)(?:[?#][^\s]*)?$",
    re.IGNORECASE,
)
# Image content-types returned by a HEAD probe for URLs without a recognizable extension
IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "image/bmp",
        "image/svg+xml",
        "image/avif",
    }
)
MEDIA_FETCH_TIMEOUT = 10
MEDIA_SIZE_LIMIT = 10 * 1024 * 1024  # 10 MB, same as XMPP


def extract_filename_from_url(url: str) -> str:
    """Extract filename from URL path or return fallback."""
    try:
        path = url.split("?", maxsplit=1)[0].rstrip("/")
        name = path.split("/")[-1]
        if name and "." in name:
            return name
    except Exception:
        pass
    return "image.png"


def rewrite_upload_url_for_fetch(url: str) -> str:
    """Rewrite XMPP upload URL to internal Docker URL when bridge cannot reach xmpp.localhost."""
    fetch_base = os.environ.get("XMPP_UPLOAD_FETCH_URL", "").rstrip("/")
    if not fetch_base:
        return url
    try:
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(url)
        # Match XMPP upload URLs (xmpp.localhost, upload.xmpp.localhost)
        if parsed.hostname and "xmpp.localhost" in parsed.hostname:
            base_parsed = urlparse(fetch_base)
            new = (
                base_parsed.scheme,
                base_parsed.netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
            return urlunparse(new)
    except Exception:
        pass
    return url


async def probe_is_image(session: aiohttp.ClientSession | None, url: str) -> bool:
    """HEAD-probe URL and return True when Content-Type indicates an image.

    Used as a fallback for URLs that don't carry a recognised file extension
    (e.g. ``https://avatars.githubusercontent.com/u/123?s=200&v=4``).
    Failures (network error, non-200) are treated as non-image.
    """
    if not session:
        return False
    try:
        async with session.head(
            url,
            timeout=aiohttp.ClientTimeout(total=5),
            allow_redirects=True,
        ) as resp:
            if resp.status != 200:
                return False
            ct = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
            return ct in IMAGE_CONTENT_TYPES
    except Exception as exc:
        logger.debug("HEAD probe failed for {}: {}", url, exc)
        return False


async def fetch_media_to_temp(session: aiohttp.ClientSession | None, url: str) -> str | None:
    """Fetch media URL to temp file. Returns path or None on failure. Caller must unlink."""
    if not session:
        return None
    fetch_url = rewrite_upload_url_for_fetch(url)
    path: str | None = None
    try:
        fd, path = tempfile.mkstemp(suffix=".media")
        os.close(fd)
        total = 0
        async with session.get(fetch_url, timeout=aiohttp.ClientTimeout(total=MEDIA_FETCH_TIMEOUT)) as resp:
            if resp.status != 200:
                os.unlink(path)
                return None
            with open(path, "wb") as f:
                async for chunk in resp.content.iter_chunked(8192):
                    total += len(chunk)
                    if total > MEDIA_SIZE_LIMIT:
                        f.close()
                        os.unlink(path)
                        return None
                    f.write(chunk)
        return path
    except Exception as exc:
        logger.debug("Failed to fetch media from {}: {}", url, exc)
        if path and os.path.exists(path):
            with contextlib.suppress(OSError):
                os.unlink(path)
        return None


async def prepare_media(session: aiohttp.ClientSession | None, content: str) -> tuple[str, File | None, str | None]:
    """Probe URL and fetch media if applicable. Returns (content, file, temp_path).

    - Non-media URL: ``(content, None, None)``
    - Successful media fetch: ``("", File(...), temp_path)``
    - Failed media fetch: ``(content, None, None)`` (graceful fallback)
    """
    content_trimmed = (content or "").strip()
    is_media = bool(MEDIA_URL_PATTERN.match(content_trimmed))
    if not is_media and content_trimmed.startswith(("http://", "https://")):
        is_media = await probe_is_image(session, content_trimmed)
    if not is_media:
        return (content, None, None)
    temp_path = await fetch_media_to_temp(session, content_trimmed)
    if temp_path:
        filename = extract_filename_from_url(content_trimmed)
        file_obj = File(temp_path, filename=filename)
        return ("", file_obj, temp_path)
    return (content, None, None)


async def upload_file(bot: commands.Bot | None, channel_id: str, data: bytes, filename: str) -> None:
    """Upload file to Discord channel."""
    if not bot:
        return

    channel = bot.get_channel(int(channel_id))
    if not channel or not isinstance(channel, TextChannel):
        logger.warning("Discord channel {} not found", channel_id)
        return

    try:
        file_obj = File(io.BytesIO(data), filename=filename)
        await channel.send(file=file_obj)
        logger.info("Uploaded {} ({} bytes) to Discord", filename, len(data))
    except Exception as exc:
        logger.exception("Failed to upload file to Discord: {}", exc)
