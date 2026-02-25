"""Protocol constants (AUDIT §3.4)."""

from __future__ import annotations

from typing import Literal

ProtocolOrigin = Literal["discord", "irc", "xmpp"]
ORIGINS: tuple[ProtocolOrigin, ...] = ("discord", "irc", "xmpp")
