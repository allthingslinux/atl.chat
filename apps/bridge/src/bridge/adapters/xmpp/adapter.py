"""XMPP adapter: Component with multi-presence (puppets), emit MessageIn; queue for outbound (AUDIT §2)."""

from __future__ import annotations

import asyncio
import contextlib
import os
import random
from typing import TYPE_CHECKING

from loguru import logger

from bridge.adapters.base import AdapterBase
from bridge.adapters.xmpp.component import XMPPComponent, _escape_jid_node
from bridge.events import MessageDeleteOut, MessageOut, ReactionOut
from bridge.gateway import Bus, ChannelRouter

if TYPE_CHECKING:
    from bridge.gateway.msgid_resolver import MessageIDResolver
    from bridge.identity import IdentityResolver

# Reconnection backoff: Prosody needs time to tear down old session before we reconnect
# (avoids "Component already connected" when reconnecting too fast)
_XMPP_BACKOFF_MIN = 5
_XMPP_BACKOFF_MAX = 120
_XMPP_MAX_ATTEMPTS = 10


async def _connect_xmpp_with_backoff(
    component: XMPPComponent,
    host: str,
    port: int,
) -> None:
    """Connect with exponential backoff on failure; reconnect on disconnect."""
    attempt = 0
    while True:
        try:
            await component.connect(host=host, port=port)
            # connect() completes when connection is established; component.disconnected
            # completes when the stream ends. Awaiting both prevents opening a second
            # connection while the first is still active (Prosody "Component already connected").
            await component.disconnected
            attempt = 0
            delay = min(_XMPP_BACKOFF_MAX, _XMPP_BACKOFF_MIN)
            jitter = random.uniform(0.8, 1.5)
            wait = delay * jitter
            logger.info("XMPP component disconnected, reconnecting in {:.1f}s", wait)
            await asyncio.sleep(wait)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            attempt += 1
            if attempt >= _XMPP_MAX_ATTEMPTS:
                logger.exception("XMPP connect failed after {} attempts", _XMPP_MAX_ATTEMPTS)
                raise
            delay = min(_XMPP_BACKOFF_MAX, _XMPP_BACKOFF_MIN * (2 ** (attempt - 1)))
            jitter = random.uniform(0.5, 1.5)
            wait = delay * jitter
            logger.warning(
                "XMPP connect failed (attempt {}): {}, retrying in {:.1f}s",
                attempt,
                exc,
                wait,
            )
            await asyncio.sleep(wait)


class XMPPAdapter(AdapterBase):
    """XMPP adapter: Component with multi-presence + outbound queue."""

    def __init__(
        self,
        bus: Bus,
        router: ChannelRouter,
        identity_resolver: IdentityResolver | None,
        msgid_resolver: MessageIDResolver | None = None,
    ) -> None:
        self._bus = bus
        self._router = router
        self._identity = identity_resolver
        self._msgid_resolver = msgid_resolver
        self._outbound: asyncio.Queue[MessageOut | MessageDeleteOut | ReactionOut] = asyncio.Queue()
        self._send_lock = asyncio.Lock()
        self._component: XMPPComponent | None = None
        self._consumer_task: asyncio.Task[None] | None = None
        self._component_task: asyncio.Future[None] | None = None

    @property
    def name(self) -> str:
        return "xmpp"

    def accept_event(self, source: str, evt: object) -> bool:
        """Accept MessageOut, MessageDeleteOut, or ReactionOut targeting XMPP."""
        if isinstance(evt, MessageOut) and evt.target_origin == "xmpp":
            return True
        if isinstance(evt, MessageDeleteOut) and evt.target_origin == "xmpp":
            return True
        return isinstance(evt, ReactionOut) and evt.target_origin == "xmpp"

    def push_event(self, source: str, evt: object) -> None:
        """Queue MessageOut, MessageDeleteOut, or ReactionOut for XMPP send."""
        if isinstance(evt, (MessageOut, MessageDeleteOut, ReactionOut)):
            if isinstance(evt, MessageOut):
                logger.info("XMPP: queued message for channel={}", evt.channel_id)
            self._outbound.put_nowait(evt)

    def _resolve_nick(self, evt: MessageOut | MessageDeleteOut | ReactionOut) -> str:
        """Fallback nick when identity resolver unavailable (dev without Portal)."""
        author = getattr(evt, "author_id", None) or ""
        display = getattr(evt, "author_display", None) or ""
        # Prefer display (e.g. "kaizen") over raw author_id (e.g. Discord snowflake)
        return (display or author)[:20] or "bridge"

    async def _resolve_nick_async(self, evt: MessageOut | MessageDeleteOut | ReactionOut) -> str:
        """Resolve XMPP nick from identity or fallback (dev mode without Portal)."""
        if self._identity and getattr(evt, "author_id", None):
            try:
                nick = await self._identity.discord_to_xmpp(evt.author_id)
                if nick:
                    return nick
            except Exception as exc:
                logger.warning(
                    "Identity lookup failed for {}: {}; falling back to display name",
                    evt.author_id,
                    exc,
                )
        return self._resolve_nick(evt)

    async def _outbound_consumer(self) -> None:
        """Drain outbound queue and send to MUC via component."""
        while True:
            try:
                evt = await self._outbound.get()
                if isinstance(evt, MessageDeleteOut):
                    logger.debug("XMPP: dequeued MessageDeleteOut discord_id={}", evt.message_id)
                    await self._handle_delete_out(evt)
                    await asyncio.sleep(0.25)
                    continue
                if isinstance(evt, ReactionOut):
                    logger.debug("XMPP: dequeued ReactionOut discord_id={} emoji={}", evt.message_id, evt.emoji)
                    await self._handle_reaction_out(evt)
                    await asyncio.sleep(0.25)
                    continue
                mapping = self._router.get_mapping_for_discord(evt.channel_id)
                if not mapping or not mapping.xmpp:
                    logger.warning("XMPP send skipped: no mapping for channel {}", evt.channel_id)
                elif not self._component:
                    logger.warning("XMPP send skipped: no component (channel={})", evt.channel_id)
                else:
                    async with self._send_lock:
                        muc_jid = mapping.xmpp.muc_jid
                        logger.debug("XMPP: processing MessageOut discord_id={} -> {}", evt.message_id, muc_jid)

                        # Resolve XMPP nick (identity or fallback for dev without Portal)
                        nick = await self._resolve_nick_async(evt)

                        # Publish vCard avatar if provided (returns hash when changed).
                        # Broadcast happens AFTER the message send because
                        # send_message_as_user calls _ensure_puppet_joined first.
                        avatar_hash: str | None = None
                        if evt.avatar_url:
                            avatar_hash = await self._component.set_avatar_for_user(evt.author_id, nick, evt.avatar_url)

                        # Check if this is an edit
                        is_edit = evt.raw.get("is_edit", False)
                        if is_edit:
                            # Look up original XMPP message ID (stored when we sent Discord→XMPP)
                            lookup_id = evt.message_id or evt.raw.get("replace_id")
                            original_xmpp_id = (
                                self._component._msgid_tracker.get_xmpp_id(lookup_id) if lookup_id else None
                            )
                            logger.debug(
                                "XMPP: edit lookup discord_msg_id={} lookup_id={} -> xmpp_id={}",
                                evt.message_id,
                                lookup_id,
                                original_xmpp_id,
                            )
                            if original_xmpp_id:
                                await self._component.send_correction_as_user(
                                    evt.author_id, muc_jid, evt.content, nick, original_xmpp_id
                                )
                                logger.info(
                                    "XMPP: sent correction for Discord msg {} -> xmpp id {}",
                                    evt.message_id,
                                    original_xmpp_id,
                                )
                            else:
                                logger.warning(
                                    "XMPP: cannot send correction: Discord message {} not in tracker "
                                    "(original may have been sent before bridge started or mapping expired)",
                                    evt.message_id,
                                )
                        else:
                            # Look up reply target XMPP message ID if replying.
                            # Prefer stanza-id (get_xmpp_id_for_reaction) so Gajim matches
                            # the reply to the displayed message (MUC uses stanza-id).
                            reply_to_xmpp_id = None
                            if evt.reply_to_id:
                                reply_to_xmpp_id = self._component._msgid_tracker.get_xmpp_id_for_reaction(
                                    evt.reply_to_id
                                )

                            # Send new message; store mapping before send so stanza-id from
                            # MUC echo can update it (required for Discord→XMPP edits)
                            content = evt.content

                            # Extract fenced code blocks and upload to paste service
                            from bridge.formatting.discord_to_xmpp import discord_to_xmpp
                            from bridge.formatting.irc_message_split import extract_code_blocks
                            from bridge.formatting.paste import upload_paste

                            processed = extract_code_blocks(content)
                            had_paste = False
                            if processed.blocks:
                                logger.debug("XMPP: found {} code block(s), uploading to paste", len(processed.blocks))
                                for i, block in enumerate(processed.blocks):
                                    url = await upload_paste(block.content, lang=block.lang)
                                    if url:
                                        label = url
                                        had_paste = True
                                        logger.debug("XMPP: paste block {} uploaded -> {}", i, url)
                                    else:
                                        snippet = block.content.replace("\n", " ").strip()[:80]
                                        label = f"[code] (paste failed) {snippet}…"
                                        logger.warning("XMPP: paste block {} upload failed, using inline snippet", i)
                                    processed.text = processed.text.replace(f"{{PASTE_{i}}}", label)
                                content = processed.text
                                logger.debug("XMPP: paste replaced content -> {!r}", content[:120])
                            else:
                                content = processed.text

                            # Parse Discord markdown -> XEP-0393 styled body + XEP-0394 spans.
                            # Only needed for Discord-origin content. IRC and XMPP content
                            # is already XEP-0393 (irc_to_xmpp converts control codes to
                            # *bold*/_italic_/etc., and XMPP content is native XEP-0393).
                            # Running discord_to_xmpp on XEP-0393 text would double-process
                            # it (e.g. *bold* → _bold_ because Discord *text* = italic).
                            origin = evt.raw.get("origin", "")
                            if origin == "discord":
                                xmpp_markup = discord_to_xmpp(content)
                                if xmpp_markup.styled_body is not None:
                                    content = xmpp_markup.styled_body
                                    markup_spans = None
                                else:
                                    content = xmpp_markup.body
                                    markup_spans = xmpp_markup.spans if xmpp_markup.has_markup else None
                            else:
                                markup_spans = None

                            # Re-upload extensionless image URLs so XMPP clients
                            # render them inline (they rely on URL file extension).
                            # Skip if content came from a paste upload — it's not an image.
                            is_media = False
                            if not had_paste and content and content.strip().startswith(("http://", "https://")):
                                logger.debug("XMPP: probing bare URL for image reupload: {}", content.strip()[:80])
                                new_url = await self._component.reupload_extensionless_image(
                                    content.strip(),
                                )
                                if new_url:
                                    logger.info("XMPP: reuploaded extensionless image -> {}", new_url)
                                    content = new_url
                                    is_media = True

                            # For IRC-origin, evt.message_id is an IRC msgid.
                            # The temporary (xmpp_id, irc_msgid) mapping is created
                            # by store_irc_xmpp_pending so the MUC echo can capture
                            # the stanza-id; resolve_irc_xmpp_pending + add_discord_id_alias
                            # later replace it with the real discord_id.
                            is_discord_origin = origin == "discord"
                            xmpp_msg_id = await self._component.send_message_as_user(
                                evt.author_id,
                                muc_jid,
                                content,
                                nick,
                                reply_to_id=reply_to_xmpp_id,
                                discord_message_id=evt.message_id if is_discord_origin else None,
                                is_media=is_media,
                                markup_spans=markup_spans,
                                media_width=evt.raw.get("media_width"),
                                media_height=evt.raw.get("media_height"),
                            )
                            if xmpp_msg_id:
                                logger.info("XMPP: sent message to {} as {}", muc_jid, nick)
                                if is_discord_origin:
                                    logger.debug(
                                        "Stored Discord→XMPP mapping: discord_id={} -> xmpp_id={}",
                                        evt.message_id,
                                        xmpp_msg_id,
                                    )
                                elif origin == "irc" and self._msgid_resolver:
                                    # Store irc_msgid→xmpp_msg_id so the Discord adapter
                                    # can link xmpp_id→discord_id after the webhook fires.
                                    self._msgid_resolver.store_irc_xmpp_pending(
                                        evt.message_id,
                                        xmpp_msg_id,
                                        muc_jid,
                                    )
                                    logger.debug(
                                        "Stored IRC→XMPP pending: irc_msgid={} -> xmpp_id={}",
                                        evt.message_id,
                                        xmpp_msg_id,
                                    )

                        # Broadcast avatar hash AFTER message send — the puppet is
                        # now guaranteed to be in the MUC (send_message_as_user
                        # calls _ensure_puppet_joined internally).
                        if avatar_hash:
                            escaped = _escape_jid_node(nick)
                            user_jid = f"{escaped}@{self._component._component_jid}"
                            bcast_key = (muc_jid, user_jid)
                            if bcast_key not in self._component._avatar_broadcast_done:
                                await self._component._broadcast_avatar_presence(user_jid, avatar_hash)
                                self._component._avatar_broadcast_done.add(bcast_key)

                await asyncio.sleep(0.25)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("XMPP send failed: {}", exc)

    async def _handle_delete_out(self, evt: MessageDeleteOut) -> None:
        """Send XMPP retraction for deleted message.

        Sends retraction with stanza-id (XEP-0424 §5.1, Gajim) and, when different,
        with origin-id so clients that match on origin-id (e.g. Converse.js) also
        remove the message. Each id is sent at most once.
        """
        if not self._component:
            return
        mapping = self._router.get_mapping_for_discord(evt.channel_id)
        if not mapping or not mapping.xmpp:
            return
        tracker = self._component._msgid_tracker
        # Prefer stanza-id (XEP-0424 §5.1 for MUC); fall back to origin-id.
        # Only send ONE retraction — sending both causes duplicate "unsupported
        # retraction" fallback messages on clients like Dino that lack XEP-0424.
        target_xmpp_id = tracker.get_xmpp_id_for_reaction(evt.message_id)
        if not target_xmpp_id:
            target_xmpp_id = tracker.get_xmpp_id(evt.message_id)
        if not target_xmpp_id:
            logger.debug("No XMPP msgid for Discord message {}; skip retraction", evt.message_id)
            return
        # Send retraction from the bridge listener JID — it's already in the MUC,
        # so no puppet join is needed (avoids nick conflicts like "admin_bridge").
        await self._component.send_retraction_as_bridge(
            mapping.xmpp.muc_jid,
            target_xmpp_id,
        )

    async def _handle_reaction_out(self, evt: ReactionOut) -> None:
        """Send XMPP reaction for ReactionOut."""
        if not self._component:
            return
        mapping = self._router.get_mapping_for_discord(evt.channel_id)
        if not mapping or not mapping.xmpp:
            return
        target_xmpp_id = self._component._msgid_tracker.get_xmpp_id_for_reaction(evt.message_id)
        if not target_xmpp_id:
            logger.warning(
                "No XMPP msgid for reaction on Discord msg {}; "
                "original may be from XMPP (ensure store) or mapping expired",
                evt.message_id,
            )
            return
        is_remove = evt.raw.get("is_remove", False)
        logger.info(
            "Sending XMPP reaction {} to msg {} (discord_id={})",
            "removal" if is_remove else evt.emoji,
            target_xmpp_id,
            evt.message_id,
        )
        nick = await self._resolve_nick_async(evt)
        await self._component.send_reaction_as_user(
            evt.author_id or "unknown",
            mapping.xmpp.muc_jid,
            target_xmpp_id,
            evt.emoji,
            nick,
            is_remove=is_remove,
        )

    async def start(self) -> None:
        """Start XMPP component."""
        component_jid = _get_component_jid()
        secret = _get_component_secret()
        server = _get_component_server()
        port = _get_component_port()

        if not component_jid or not secret or not server:
            logger.warning("XMPP component config incomplete; XMPP adapter disabled")
            return

        if not self._identity:
            logger.info("XMPP adapter running without Portal (dev mode): using fallback nicks")

        mappings = self._router.all_mappings()
        xmpp_mappings = [m for m in mappings if m.xmpp]
        if not xmpp_mappings:
            logger.warning("No XMPP mappings; XMPP adapter disabled")
            return

        self._component = XMPPComponent(
            component_jid,
            secret,
            server,
            port,
            self._bus,
            self._router,
            self._identity,
        )
        if self._msgid_resolver:
            self._msgid_resolver.register_xmpp(self._component)
        self._bus.register(self)
        self._consumer_task = asyncio.create_task(self._outbound_consumer())
        # Reconnect loop: connect with backoff on failure, retry on disconnect
        self._component_task = asyncio.create_task(_connect_xmpp_with_backoff(self._component, host=server, port=port))
        logger.info("XMPP component started: {} (reconnect enabled)", component_jid)

    async def stop(self) -> None:
        """Stop XMPP component."""
        self._bus.unregister(self)
        if self._consumer_task:
            self._consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._consumer_task
        if self._component:
            self._component.disconnect()
        if self._component_task:
            self._component_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._component_task
        self._component = None
        self._component_task = None


def _get_component_jid() -> str | None:
    return os.environ.get("BRIDGE_XMPP_COMPONENT_JID")


def _get_component_secret() -> str | None:
    return os.environ.get("BRIDGE_XMPP_COMPONENT_SECRET")


def _get_component_server() -> str | None:
    return os.environ.get("BRIDGE_XMPP_COMPONENT_SERVER")


def _get_component_port() -> int:
    return int(os.environ.get("BRIDGE_XMPP_COMPONENT_PORT", "5347"))
