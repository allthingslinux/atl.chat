"""XMPP adapter package (AUDIT §2.B)."""

from bridge.adapters.xmpp.adapter import XMPPAdapter
from bridge.adapters.xmpp.component import XMPPComponent, _escape_jid_node
from bridge.adapters.xmpp.msgid import XMPPMessageIDTracker, XMPPMessageMapping

__all__ = [
    "XMPPAdapter",
    "XMPPComponent",
    "XMPPMessageIDTracker",
    "XMPPMessageMapping",
    "_escape_jid_node",
]
