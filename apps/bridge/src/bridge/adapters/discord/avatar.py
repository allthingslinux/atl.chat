"""Discord avatar resolution: XMPP avatar fallback for IRC-origin messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bridge.events import MessageOut
    from bridge.gateway import ChannelRouter


def resolve_xmpp_avatar_fallback(evt: MessageOut, router: ChannelRouter) -> str | None:
    """Try to resolve an XMPP avatar for IRC-origin messages with no avatar.

    Uses the IRC nick as the XMPP node (localpart) and probes Prosody's
    PEP/vCard avatar endpoints. Only applies when the channel mapping has
    an XMPP target so we can derive the domain.
    """
    origin = (evt.raw or {}).get("origin", "")
    if origin != "irc":
        return None
    mapping = router.get_mapping_for_discord(evt.channel_id)
    if not mapping or not mapping.xmpp:
        return None

    from bridge.avatar import resolve_xmpp_avatar_url, xmpp_domain_from_muc_jid

    base_domain = xmpp_domain_from_muc_jid(mapping.xmpp.muc_jid)
    # Use IRC nick (author_display) as XMPP node — common for users on both protocols
    node = evt.author_display.lower()
    return resolve_xmpp_avatar_url(base_domain, node)
