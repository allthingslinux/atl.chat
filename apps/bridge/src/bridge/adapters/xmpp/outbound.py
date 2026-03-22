"""XMPP outbound message sending — extracted from XMPPComponent.

All functions receive the component instance as the first parameter.
"""

from __future__ import annotations

import re as _re
import time
import uuid
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape as _xml_escape

from loguru import logger
from slixmpp import JID

from bridge.adapters.xmpp.component import _BARE_URL_RE, _escape_jid_node

if TYPE_CHECKING:
    from bridge.adapters.xmpp.component import XMPPComponent

#: Fallback body text included in retraction stanzas for clients that
#: do not support XEP-0424 Message Retraction (XEP-0424 §3 Example 4).
RETRACTION_FALLBACK_BODY = "/me retracted a previous message, but it's unsupported by your client."


async def send_message_as_user(
    comp: XMPPComponent,
    discord_id: str,
    muc_jid: str,
    content: str,
    nick: str,
    xmpp_msg_id: str | None = None,
    reply_to_id: str | None = None,
    *,
    discord_message_id: str | None = None,
    is_media: bool = False,
    markup_spans: list | None = None,
    media_width: int | None = None,
    media_height: int | None = None,
    spoiler: bool = False,
    spoiler_reason: str | None = None,
    reply_to_author_nick: str | None = None,
    reply_to_body: str | None = None,
) -> str:
    """Send message to MUC from a specific Discord user's JID. Returns XMPP message ID.

    When discord_message_id is provided, stores (xmpp_id, discord_message_id, muc_jid)
    before sending so stanza-id from MUC echo can update the mapping (Discord→XMPP edits).
    """
    escaped_nick = _escape_jid_node(nick)
    user_jid = f"{escaped_nick}@{comp._component_jid}"
    # Record before send for echo detection fallback (when get_jid_property returns None)
    comp._recent_sent_nicks[(muc_jid, nick)] = None
    await comp._ensure_puppet_joined(muc_jid, user_jid, nick)

    try:
        # XEP-0382 spoiler: use pipeline flag (content already stripped) or detect inline ||markers||
        spoiler_hint: str | None = None
        if spoiler:
            spoiler_hint = spoiler_reason or ""
        else:
            whole_spoiler_re = _re.compile(r"^\|\|(.+)\|\|$", _re.DOTALL)
            inline_spoiler_re = _re.compile(r"\|\|([^|]+)\|\|")
            whole_match = whole_spoiler_re.match(content.strip())
            if whole_match:
                content = whole_match.group(1).strip()
                spoiler_hint = ""
            elif "||" in content:
                content = inline_spoiler_re.sub(r"\1", content)
                spoiler_hint = ""

        msg = comp.make_message(
            mto=JID(muc_jid),
            mfrom=JID(user_jid),
            mbody=content[:4000],
            mtype="groupchat",
        )
        if xmpp_msg_id:
            msg["id"] = xmpp_msg_id
        elif not msg.get("id"):
            msg["id"] = f"bridge-{int(time.time() * 1000)}-{uuid.uuid4().hex[:12]}"

        msg_id = msg["id"]
        if discord_message_id:
            comp._msgid_tracker.store(msg_id, discord_message_id, muc_jid)

        if spoiler_hint is not None:
            msg.enable("spoiler")
            if spoiler_hint:
                msg["spoiler"].xml.text = spoiler_hint

        if reply_to_id:
            try:
                from slixmpp.plugins.xep_0461.stanza import Reply as _Reply

                reply: _Reply = msg.enable("reply")  # type: ignore[assignment]
                # XEP-0461 §3: 'to' SHOULD be the full JID of the quoted author.
                # For MUC groupchat that is room@muc/nick. Use author nick if known,
                # otherwise fall back to the bare room JID (still valid per spec).
                if reply_to_author_nick:
                    escaped_reply_nick = _escape_jid_node(reply_to_author_nick)
                    reply["to"] = JID(f"{muc_jid}/{escaped_reply_nick}")
                else:
                    reply["to"] = JID(muc_jid)
                reply["id"] = reply_to_id

                # Add quoted fallback so non-XEP-0461 clients see "> nick:\n> text\n"
                # add_quoted_fallback() prepends the quote block to msg["body"] and
                # attaches the XEP-0428 <fallback for="urn:xmpp:reply:0"> element.
                if reply_to_body is not None:
                    reply.add_quoted_fallback(
                        _xml_escape(reply_to_body[:200]),  # XML-escape and truncate to avoid oversized stanzas
                        nickname=reply_to_author_nick,
                    )
                else:
                    # Minimal fallback for when quoted content is unavailable
                    fallback_prefix = "> [reply]\n"
                    msg["body"] = fallback_prefix + (msg["body"] or "")
                    fb = msg.enable("fallback")
                    fb["for"] = "urn:xmpp:reply:0"
                    fb_body = fb.enable("body")
                    fb_body["start"] = 0
                    fb_body["end"] = len(fallback_prefix)
            except Exception as exc:
                logger.debug("XEP-0461 reply stanza attach failed: {}", exc)

        # Add origin-id (XEP-0359) so MUC preserves it
        if msg_id:
            try:
                msg.enable("origin_id")
                msg["origin_id"]["id"] = str(msg_id)
            except Exception:
                pass

        # Attach XEP-0066 OOB only when the URL is confirmed media.
        # OOB (Out of Band Data) tells XMPP clients to render the URL as an
        # inline image/video rather than a plain text link. We only attach it
        # when the body is a bare URL confirmed as media to avoid clients
        # trying to render non-media URLs as images.
        body_stripped = content[:4000].strip()
        if is_media and _BARE_URL_RE.match(body_stripped):
            try:
                msg.enable("oob")
                msg["oob"]["url"] = body_stripped
            except Exception:
                pass

            if media_width and media_height:
                try:
                    file_ns = "urn:xmpp:file:metadata:0"
                    file_el = ET.Element(f"{{{file_ns}}}file")
                    w_el = ET.SubElement(file_el, f"{{{file_ns}}}width")
                    w_el.text = str(media_width)
                    h_el = ET.SubElement(file_el, f"{{{file_ns}}}height")
                    h_el.text = str(media_height)
                    msg.xml.append(file_el)
                except Exception as exc:
                    logger.debug("XEP-0446 file metadata attach failed: {}", exc)

        # Attach XEP-0394 markup spans
        if markup_spans:
            try:
                from slixmpp.plugins.xep_0394.stanza import Markup, Span

                ns = "urn:xmpp:markup:0"
                slixmpp_types = {"emphasis", "code", "deleted"}

                markup_el = Markup()
                for span in markup_spans:
                    s = Span()
                    s["start"] = span.start
                    s["end"] = span.end
                    known = [t for t in span.types if t in slixmpp_types]
                    if known:
                        s["types"] = known
                    for t in span.types:
                        if t not in slixmpp_types:
                            s.xml.append(ET.Element(f"{{{ns}}}{t}"))
                    markup_el.append(s)
                msg.append(markup_el)
            except Exception as exc:
                logger.debug("XEP-0394 markup attach failed: {}", exc)

        msg.send()

        logger.debug("sent message {} from {} to {}", msg_id, user_jid, muc_jid)
        return msg_id
    except Exception as exc:
        logger.exception("failed to send message as {}: {}", user_jid, exc)
        return ""


async def send_reaction_as_user(
    comp: XMPPComponent,
    discord_id: str,
    muc_jid: str,
    target_msg_id: str,
    emoji: str,
    nick: str,
    *,
    is_remove: bool = False,
) -> None:
    """Send reaction (add or remove) to a message from a specific Discord user's JID.

    XEP-0444 requires sending the full reaction set per-user per-message.
    We accumulate state in ``comp._reactions_by_user`` (keyed by
    ``(target_msg_id, nick)``) and always send the complete set.
    """
    escaped_nick = _escape_jid_node(nick)
    user_jid = f"{escaped_nick}@{comp._component_jid}"
    comp._recent_sent_nicks[(muc_jid, nick)] = None
    await comp._ensure_puppet_joined(muc_jid, user_jid, nick)

    reactions_plugin = comp.plugin.get("xep_0444", None)
    if not reactions_plugin:
        logger.error("XEP-0444 plugin not available")
        return

    try:
        # Accumulate full reaction state per (message, user)
        cache_key = (target_msg_id, nick)
        prev_set = set(comp._reactions_by_user.get(cache_key, frozenset()))
        if is_remove:
            prev_set.discard(emoji)
        else:
            prev_set.add(emoji)
        # Update cache with new full set
        comp._reactions_by_user[cache_key] = frozenset(prev_set)

        msg = comp.make_message(
            mto=JID(muc_jid),
            mfrom=JID(user_jid),
            mtype="groupchat",
        )
        reactions_plugin.set_reactions(msg, target_msg_id, prev_set)
        msg.enable("no-store")
        msg.send()
        logger.info(
            "sent reaction {} (full set: {}) to message {} in room {} (from IRC/Discord)",
            "removal" if is_remove else emoji,
            prev_set or "empty",
            target_msg_id,
            muc_jid,
        )
    except Exception as exc:
        logger.exception("Failed to send reaction: {}", exc)


async def send_retraction_as_user(
    comp: XMPPComponent,
    discord_id: str,
    muc_jid: str,
    target_msg_id: str,
    nick: str,
) -> None:
    """Send message retraction from a specific Discord user's JID.

    Builds the stanza manually to include:
    - <retract xmlns="urn:xmpp:message-retract:1" id="..."/>
    - <body> with fallback text for non-supporting clients
    - <fallback xmlns="urn:xmpp:fallback:0" for="urn:xmpp:message-retract:1"/>
    - <store xmlns="urn:xmpp:hints"/> for archival
    (Requirements 25.1, 25.2)
    """
    escaped_nick = _escape_jid_node(nick)
    user_jid = f"{escaped_nick}@{comp._component_jid}"
    comp._recent_sent_nicks[(muc_jid, nick)] = None
    await comp._ensure_puppet_joined(muc_jid, user_jid, nick)

    try:
        msg = comp.make_message(
            mto=JID(muc_jid),
            mfrom=JID(user_jid),
            mbody=RETRACTION_FALLBACK_BODY,
            mtype="groupchat",
        )
        msg["id"] = f"bridge-retract-{uuid.uuid4().hex}"
        msg["retract"]["id"] = target_msg_id
        fb = msg.enable("fallback")
        fb["for"] = "urn:xmpp:message-retract:1"
        msg.enable("store")
        msg.send()
        logger.info("sent retraction for message {} to room {} (from IRC/Discord)", target_msg_id, muc_jid)
    except Exception as exc:
        logger.exception("Failed to send retraction: {}", exc)


async def send_retraction_as_bridge(
    comp: XMPPComponent,
    muc_jid: str,
    target_msg_id: str,
) -> None:
    """Send message retraction from the bridge listener JID (no puppet join needed).

    Builds the stanza manually to include:
    - <retract xmlns="urn:xmpp:message-retract:1" id="..."/>
    - <body> with fallback text for non-supporting clients
    - <fallback xmlns="urn:xmpp:fallback:0" for="urn:xmpp:message-retract:1"/>
    - <store xmlns="urn:xmpp:hints"/> for archival
    (Requirements 25.1, 25.2)
    """
    bridge_jid = f"bridge@{comp._component_jid}"

    try:
        msg = comp.make_message(
            mto=JID(muc_jid),
            mfrom=JID(bridge_jid),
            mbody=RETRACTION_FALLBACK_BODY,
            mtype="groupchat",
        )
        msg["id"] = f"bridge-retract-{uuid.uuid4().hex}"
        msg["retract"]["id"] = target_msg_id
        fb = msg.enable("fallback")
        fb["for"] = "urn:xmpp:message-retract:1"
        msg.enable("store")
        msg.send()
        logger.info("sent retraction for message {} to room {} (from bridge)", target_msg_id, muc_jid)
    except Exception as exc:
        logger.exception("Failed to send retraction from bridge: {}", exc)


async def send_correction_as_user(
    comp: XMPPComponent,
    discord_id: str,
    muc_jid: str,
    content: str,
    nick: str,
    original_xmpp_id: str,
) -> None:
    """Send message correction (XEP-0308) to MUC via slixmpp's build_correction."""
    escaped_nick = _escape_jid_node(nick)
    user_jid = f"{escaped_nick}@{comp._component_jid}"
    comp._recent_sent_nicks[(muc_jid, nick)] = None
    await comp._ensure_puppet_joined(muc_jid, user_jid, nick)

    try:
        xep_0308 = comp.plugin.get("xep_0308", None)
        if xep_0308:
            msg = xep_0308.build_correction(
                id_to_replace=original_xmpp_id,
                mto=JID(muc_jid),
                mfrom=JID(user_jid),
                mtype="groupchat",
                mbody=content[:4000],
            )
        else:
            msg = comp.make_message(
                mto=JID(muc_jid),
                mfrom=JID(user_jid),
                mbody=content[:4000],
                mtype="groupchat",
            )
            msg["id"] = f"bridge-correct-{uuid.uuid4().hex}"
            msg.enable("replace")
            msg["replace"]["id"] = original_xmpp_id
        msg.send()
        logger.debug(
            "sent correction: replace_id={} from={} to={} body_len={}",
            original_xmpp_id,
            user_jid,
            muc_jid,
            len(content),
        )
    except Exception as exc:
        logger.exception("failed to send correction as {}: {}", user_jid, exc)


async def send_composing_as_bridge(comp: XMPPComponent, muc_jid: str) -> None:
    """Send XEP-0085 <composing/> chatstate from the bridge listener to the MUC.

    Uses XEP-0334 no-store hint so the indicator is not archived.
    """
    bridge_jid = f"bridge@{comp._component_jid}"
    try:
        msg = comp.make_message(
            mto=JID(muc_jid),
            mfrom=JID(bridge_jid),
            mtype="groupchat",
        )
        msg["chat_state"] = "composing"
        msg.enable("no-store")
        msg.send()
        logger.debug("sent chatstate composing to {}", muc_jid)
    except Exception as exc:
        logger.debug("chatstate composing send failed for {}: {}", muc_jid, exc)


async def send_paused_as_bridge(comp: XMPPComponent, muc_jid: str) -> None:
    """Send XEP-0085 <paused/> chatstate from the bridge listener to the MUC.

    Clears the composing indicator on XMPP clients. Uses XEP-0334 no-store hint.
    """
    bridge_jid = f"bridge@{comp._component_jid}"
    try:
        msg = comp.make_message(
            mto=JID(muc_jid),
            mfrom=JID(bridge_jid),
            mtype="groupchat",
        )
        msg["chat_state"] = "paused"
        msg.enable("no-store")
        msg.send()
        logger.debug("sent chatstate paused to {}", muc_jid)
    except Exception as exc:
        logger.debug("chatstate paused send failed for {}: {}", muc_jid, exc)
