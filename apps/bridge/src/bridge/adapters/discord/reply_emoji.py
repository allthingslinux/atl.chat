"""Reply emoji setup and cache for OOYE-style -# > subtext reply lines.

On bot ready, uploads L1 and L2 as Discord application emojis (once, idempotent).
get_reply_prefix() returns <:L1:id><:L2:id> when available, or ↪ as fallback.

L1 is a corner bracket shape, L2 is a horizontal bar — together they form the
same visual reply line that Discord uses natively for its reply UI.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from discord.ext import commands

_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"
_EMOJI_NAMES = ("L1", "L2")

# Module-level cache: name -> emoji_id string
_cache: dict[str, str] = {}


def get_reply_prefix() -> str:
    """Return <:L1:id><:L2:id> if emojis are set up, else ↪ as text fallback."""
    if _cache.get("L1") and _cache.get("L2"):
        return f"<:L1:{_cache['L1']}><:L2:{_cache['L2']}>"
    return "↪"


async def setup_reply_emojis(bot: commands.Bot) -> None:
    """Ensure L1 and L2 application emojis exist and populate the in-memory cache.

    Safe to call on every on_ready — existing emojis are reused, not re-uploaded.
    """
    try:
        existing = await bot.fetch_application_emojis()
        existing_by_name = {e.name: str(e.id) for e in existing}

        for name in _EMOJI_NAMES:
            if name in existing_by_name:
                _cache[name] = existing_by_name[name]
                logger.debug("reply emoji {} already exists (id={})", name, _cache[name])
            else:
                asset_path = _ASSETS_DIR / f"{name}.png"
                try:
                    data = asset_path.read_bytes()
                except (FileNotFoundError, OSError) as exc:
                    logger.warning(
                        "Reply emoji asset not found at {}; skipping upload (will use ↪ fallback): {}",
                        asset_path,
                        exc,
                    )
                    continue
                emoji = await bot.create_application_emoji(name=name, image=data)
                _cache[name] = str(emoji.id)
                logger.info("uploaded reply emoji {} (id={})", name, _cache[name])
    except Exception as exc:
        logger.warning("could not set up reply emojis, will use ↪ fallback: {}", exc)
