"""XMPP adapter: Component with multi-presence (puppets), emit MessageIn; queue for outbound (AUDIT §2)."""

from __future__ import annotations

import asyncio
import contextlib
import os
from typing import TYPE_CHECKING

from loguru import logger

from bridge.adapters.xmpp_component import XMPPComponent
from bridge.events import MessageDeleteOut, MessageOut, ReactionOut
from bridge.gateway import Bus, ChannelRouter

if TYPE_CHECKING:
    from bridge.identity import IdentityResolver


class XMPPAdapter:
    """XMPP adapter: Component with multi-presence + outbound queue."""

    def __init__(
        self,
        bus: Bus,
        router: ChannelRouter,
        identity_resolver: IdentityResolver | None,
    ) -> None:
        self._bus = bus
        self._router = router
        self._identity = identity_resolver
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
            nick = await self._identity.discord_to_xmpp(evt.author_id)
            if nick:
                return nick
        return self._resolve_nick(evt)

    async def _outbound_consumer(self) -> None:
        """Drain outbound queue and send to MUC via component."""
        while True:
            try:
                evt = await self._outbound.get()
                if isinstance(evt, MessageDeleteOut):
                    await self._handle_delete_out(evt)
                    await asyncio.sleep(0.25)
                    continue
                if isinstance(evt, ReactionOut):
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

                        # Resolve XMPP nick (identity or fallback for dev without Portal)
                        nick = await self._resolve_nick_async(evt)

                        # Set avatar if provided
                        if evt.avatar_url:
                            await self._component.set_avatar_for_user(evt.author_id, nick, evt.avatar_url)

                        # Check if this is an edit
                        is_edit = evt.raw.get("is_edit", False)
                        if is_edit:
                            # Look up original XMPP message ID (stored when we sent Discord→XMPP)
                            lookup_id = evt.message_id or evt.raw.get("replace_id")
                            original_xmpp_id = (
                                self._component._msgid_tracker.get_xmpp_id(lookup_id) if lookup_id else None
                            )
                            logger.debug(
                                "Discord edit lookup: discord_msg_id={} lookup_id={} -> xmpp_id={}",
                                evt.message_id,
                                lookup_id,
                                original_xmpp_id,
                            )
                            if original_xmpp_id:
                                await self._component.send_correction_as_user(
                                    evt.author_id, muc_jid, evt.content, nick, original_xmpp_id
                                )
                                logger.info(
                                    "Sent XMPP correction for Discord msg {} -> xmpp id {}",
                                    evt.message_id,
                                    original_xmpp_id,
                                )
                            else:
                                logger.warning(
                                    "Cannot send XMPP correction: Discord message {} not in tracker "
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
                            xmpp_msg_id = await self._component.send_message_as_user(
                                evt.author_id,
                                muc_jid,
                                evt.content,
                                nick,
                                reply_to_id=reply_to_xmpp_id,
                                discord_message_id=evt.message_id,
                            )
                            if xmpp_msg_id:
                                logger.info("XMPP: sent message to {} as {}", muc_jid, nick)
                                logger.debug(
                                    "Stored Discord→XMPP mapping: discord_id={} -> xmpp_id={}",
                                    evt.message_id,
                                    xmpp_msg_id,
                                )

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
        stanza_id = tracker.get_xmpp_id_for_reaction(evt.message_id)
        primary_id = tracker.get_xmpp_id(evt.message_id)
        ids_to_send = []
        if stanza_id:
            ids_to_send.append(stanza_id)
        if primary_id and primary_id not in ids_to_send:
            ids_to_send.append(primary_id)
        if not ids_to_send:
            logger.debug("No XMPP msgid for Discord message {}; skip retraction", evt.message_id)
            return
        nick = await self._resolve_nick_async(evt)
        for target_xmpp_id in ids_to_send:
            await self._component.send_retraction_as_user(
                evt.author_id or "unknown",
                mapping.xmpp.muc_jid,
                target_xmpp_id,
                nick,
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
            "Sending XMPP reaction %s to msg %s (discord_id=%s)",
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
        self._bus.register(self)
        self._consumer_task = asyncio.create_task(self._outbound_consumer())
        # slixmpp connect() returns a Future/Task, not a coroutine
        self._component_task = self._component.connect()
        logger.info("XMPP component started: {}", component_jid)

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
