"""Protocol adapters. Each implements base.AdapterInterface."""

from bridge.adapters.base import AdapterBase
from bridge.adapters.disc import DiscordAdapter
from bridge.adapters.irc import IRCAdapter

__all__ = ["AdapterBase", "DiscordAdapter", "IRCAdapter"]
