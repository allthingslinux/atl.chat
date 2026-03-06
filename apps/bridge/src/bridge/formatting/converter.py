"""Registry-based format conversion via the formatting IR.

convert            — convert content from origin protocol format to target format
strip_formatting   — parse content and return plain text (no formatting markers)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from bridge.formatting.irc_codes import emit_irc_codes, parse_irc_codes
from bridge.formatting.markdown import emit_discord_markdown, parse_discord_markdown
from bridge.formatting.primitives import FormattedText
from bridge.formatting.xmpp_styling import emit_xep0393, parse_xep0393

# Use the existing ProtocolOrigin type from core.constants when available,
# but define a local alias so the module is self-contained for typing.
ProtocolName = Literal["discord", "irc", "xmpp"]

# ---------------------------------------------------------------------------
# Parser / emitter registries
# ---------------------------------------------------------------------------

_PARSERS: dict[ProtocolName, Callable[[str], FormattedText]] = {
    "discord": parse_discord_markdown,
    "irc": parse_irc_codes,
    "xmpp": parse_xep0393,
}

_EMITTERS: dict[ProtocolName, Callable[[FormattedText], str]] = {
    "discord": emit_discord_markdown,
    "irc": emit_irc_codes,
    "xmpp": emit_xep0393,
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def convert(content: str, origin: ProtocolName, target: ProtocolName) -> str:
    """Convert *content* from *origin* protocol format to *target* format via IR.

    Returns *content* unchanged when *origin* equals *target*.
    """
    if origin == target:
        return content
    parser = _PARSERS[origin]
    emitter = _EMITTERS[target]
    ir = parser(content)
    return emitter(ir)


def strip_formatting(content: str, protocol: ProtocolName) -> str:
    """Parse *content* as *protocol* formatting and return just the plain text.

    Useful for property tests that need to compare semantic content
    independent of formatting markers.
    """
    parser = _PARSERS[protocol]
    ir = parser(content)
    return ir.plain
