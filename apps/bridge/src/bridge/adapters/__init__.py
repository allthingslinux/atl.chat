"""Protocol adapters. Each implements BridgeAdapter (EventTarget + name, start, stop)."""

from bridge.adapters.base import AdapterBase
from bridge.adapters.discord import DiscordAdapter
from bridge.adapters.irc import IRCAdapter
from bridge.adapters.xmpp import XMPPAdapter
from bridge.core.events import BridgeAdapter

__all__ = ["AdapterBase", "BridgeAdapter", "DiscordAdapter", "IRCAdapter", "XMPPAdapter"]
