"""Default pipeline step implementations (Design §D6).

Each function matches the ``TransformStep`` protocol::

    (content: str, ctx: TransformContext) -> str | None

Steps
-----
strip_reply_fallback  – remove reply fallback lines for XMPP/IRC origins
unwrap_spoiler        – extract spoiler markers into ``ctx.spoiler``
format_convert        – delegate to ``formatting.converter.convert``
wrap_spoiler          – apply target-protocol spoiler markers
add_reply_fallback    – prepend reply indicator for IRC targets
make_content_filter   – factory returning a step that drops filtered content
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from bridge.formatting.converter import convert
from bridge.formatting.irc_codes import COLOR, RESET, detect_irc_spoilers
from bridge.formatting.primitives import strip_invalid_xml_chars
from bridge.gateway.pipeline import TransformContext

if TYPE_CHECKING:
    from bridge.gateway.pipeline import TransformStep

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Discord spoiler markers: ||text||
_DISCORD_SPOILER_RE = re.compile(r"\|\|(.+?)\|\|", re.DOTALL)

# XMPP XEP-0461 reply fallback: leading lines starting with "> "
_XMPP_REPLY_FALLBACK_RE = re.compile(r"^(> [^\n]*\n?)+", re.MULTILINE)

# IRC reply fallback: leading line with <nick> prefix or similar
_IRC_REPLY_FALLBACK_RE = re.compile(r"^<[^>]+> .+\n?")


# ---------------------------------------------------------------------------
# Step 1: strip_reply_fallback
# ---------------------------------------------------------------------------


def strip_reply_fallback(content: str, ctx: TransformContext) -> str:
    """Remove reply fallback lines when ``reply_to_id`` is present.

    For XMPP origins, strips leading ``> `` prefixed lines (XEP-0461).
    For IRC origins, strips a leading ``<nick> ...`` line.
    """
    if not ctx.reply_to_id:
        return content

    if ctx.origin == "xmpp":
        stripped = _XMPP_REPLY_FALLBACK_RE.sub("", content).lstrip("\n")
        return stripped if stripped else content
    if ctx.origin == "irc":
        stripped = _IRC_REPLY_FALLBACK_RE.sub("", content).lstrip("\n")
        return stripped if stripped else content

    return content


# ---------------------------------------------------------------------------
# Step 2: unwrap_spoiler
# ---------------------------------------------------------------------------


def unwrap_spoiler(content: str, ctx: TransformContext) -> str:
    """Extract spoiler markers and set ``ctx.spoiler``.

    * **Discord** – strips ``||…||`` markers, sets flag.
    * **IRC** – detects fg==bg color regions via :func:`detect_irc_spoilers`.
    * **XMPP** – checks ``ctx.raw`` for XEP-0382 spoiler element.
    """
    if ctx.origin == "discord":
        if _DISCORD_SPOILER_RE.search(content):
            ctx.spoiler = True
            content = _DISCORD_SPOILER_RE.sub(r"\1", content)
        return content

    if ctx.origin == "irc":
        if detect_irc_spoilers(content):
            ctx.spoiler = True
        return content

    if ctx.origin == "xmpp":
        # XEP-0382: spoiler info lives in the stanza, not inline text.
        if ctx.raw.get("spoiler") or ctx.raw.get("xep_0382"):
            ctx.spoiler = True
            reason = ctx.raw.get("spoiler_reason")
            if reason:
                ctx.spoiler_reason = reason
        return content

    return content


# ---------------------------------------------------------------------------
# Step 3: format_convert
# ---------------------------------------------------------------------------


def format_convert(content: str, ctx: TransformContext) -> str:
    """Delegate to :func:`formatting.converter.convert`.

    When ``ctx.raw["unstyled"]`` is set (XEP-0393 §6), the XMPP sender
    explicitly opted out of styling — skip format conversion so the body
    is relayed as plain text.
    """
    if ctx.raw.get("unstyled"):
        return content
    return convert(content, ctx.origin, ctx.target)


# ---------------------------------------------------------------------------
# Step 4: wrap_spoiler
# ---------------------------------------------------------------------------


def wrap_spoiler(content: str, ctx: TransformContext) -> str:
    """Apply target-protocol spoiler markers when ``ctx.spoiler`` is set.

    * **Discord** – wraps with ``||content||``.
    * **IRC** – wraps with fg==bg color codes (``\\x0301,01content\\x03``).
    * **XMPP** – sets ``ctx.raw["spoiler"]`` for the adapter to emit XEP-0382.
    """
    if not ctx.spoiler:
        return content

    if ctx.target == "discord":
        return f"||{content}||"

    if ctx.target == "irc":
        # fg==bg color 1 (black on black) — common IRC spoiler convention
        return f"{COLOR}01,01{content}{RESET}"

    if ctx.target == "xmpp":
        # XEP-0382 is a stanza-level element; signal the adapter via ctx.raw.
        ctx.raw["spoiler"] = True
        if ctx.spoiler_reason:
            ctx.raw["spoiler_reason"] = ctx.spoiler_reason
        return content

    return content


# ---------------------------------------------------------------------------
# Step 5: add_reply_fallback
# ---------------------------------------------------------------------------


def add_reply_fallback(content: str, ctx: TransformContext) -> str:
    """Prepend a reply indicator for IRC targets when reply context exists.

    When ``reply_quoted_content`` and optionally ``reply_quoted_author`` are
    available in ``ctx.raw``, format as ``author: > quoted | reply`` (the
    traditional IRC reply style).  Without quoted content, the message is
    returned unchanged (the reply reference is handled by the IRC adapter
    via ``+draft/reply`` tags when available).
    """
    if ctx.target != "irc" or not ctx.reply_to_id:
        return content

    quoted = ctx.raw.get("reply_quoted_content")
    if not quoted:
        return content

    # Check first line doesn't already contain a quote marker
    first_line = content.split("\n", maxsplit=1)[0] if content else ""
    if ">" in first_line:
        return content

    quoted_clean = quoted.strip()
    if not quoted_clean:
        return content
    # Ensure > prefix, collapse newlines for IRC single-line format
    if not quoted_clean.startswith(">"):
        quoted_clean = "> " + quoted_clean
    quoted_line = " ".join(quoted_clean.splitlines())
    reply_part = f"{quoted_line} | {content}"
    content = f"{ctx.raw['reply_quoted_author']}: {reply_part}" if ctx.raw.get("reply_quoted_author") else reply_part
    ctx.raw["reply_fallback_added"] = True
    return content


# ---------------------------------------------------------------------------
# Step 6: content_filter (factory)
# ---------------------------------------------------------------------------


def make_content_filter(patterns: list[re.Pattern[str]]) -> TransformStep:
    """Return a :class:`TransformStep` that drops content matching *patterns*.

    Empty content is never filtered (Requirement 4.8).
    """

    def content_filter(content: str, ctx: TransformContext) -> str | None:
        if not content:
            return content  # empty → pass through unchanged
        for pat in patterns:
            if pat.search(content):
                return None  # drop
        return content

    return content_filter


# ---------------------------------------------------------------------------
# Step: strip_invalid_xml (before content_filter)
# ---------------------------------------------------------------------------


def strip_invalid_xml(content: str, ctx: TransformContext) -> str:
    """Strip characters invalid in XML 1.0 when the target is XMPP.

    Only applies when ``ctx.target == "xmpp"``; other targets pass through
    unchanged.  Delegates to :func:`formatting.primitives.strip_invalid_xml_chars`.
    """
    if ctx.target != "xmpp":
        return content
    return strip_invalid_xml_chars(content)
