"""IRC adapter package (AUDIT §2.B)."""

from bridge.adapters.irc.adapter import IRCAdapter
from bridge.adapters.irc.client import _MAX_ATTEMPTS, IRCClient, _connect_with_backoff
from bridge.adapters.irc.msgid import MessageIDTracker, MessageMapping, ReactionTracker
from bridge.adapters.irc.puppet import IRCPuppet, IRCPuppetManager
from bridge.adapters.irc.throttle import TokenBucket

__all__ = [
    "_MAX_ATTEMPTS",
    "IRCAdapter",
    "IRCClient",
    "IRCPuppet",
    "IRCPuppetManager",
    "MessageIDTracker",
    "MessageMapping",
    "ReactionTracker",
    "TokenBucket",
    "_connect_with_backoff",
]
