"""Discord adapter package (AUDIT §2.B)."""

from bridge.adapters.discord.adapter import DiscordAdapter
from bridge.adapters.discord.webhook import _ensure_valid_username

__all__ = ["DiscordAdapter", "_ensure_valid_username"]
