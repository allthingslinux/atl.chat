"""XMPP adapter: Component with multi-presence (puppets), emit MessageIn; queue for outbound (AUDIT §2)."""

from __future__ import annotations

import asyncio
import contextlib
import os
from typing import TYPE_CHECKING

from loguru import logger

from bridge.adapters.xmpp_component import XMPPComponent
from bridge.events import MessageOut
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
        self._outbound: asyncio.Queue[MessageOut] = asyncio.Queue()
        self._component: XMPPComponent | None = None
        self._consumer_task: asyncio.Task | None = None
        self._component_task: asyncio.Task | None = None

    @property
    def name(self) -> str:
        return "xmpp"

    def accept_event(self, source: str, evt: object) -> bool:
        """Accept MessageOut targeting XMPP."""
        return isinstance(evt, MessageOut) and evt.target_origin == "xmpp"

    def push_event(self, source: str, evt: object) -> None:
        """Queue MessageOut for XMPP send."""
        if isinstance(evt, MessageOut):
            self._outbound.put_nowait(evt)

    async def _outbound_consumer(self) -> None:
        """Drain outbound queue and send to MUC via component."""
        while True:
            try:
                evt = await self._outbound.get()
                mapping = self._router.get_mapping_for_discord(evt.channel_id)
                if mapping and mapping.xmpp and self._component and self._identity:
                    muc_jid = mapping.xmpp.muc_jid

                    # Get Discord user's XMPP nick from identity
                    nick = await self._identity.discord_to_xmpp(evt.author_id)
                    if not nick:
                        # Fallback to Discord display name
                        nick = evt.author_id[:20]  # Truncate for safety

                    # Set avatar if provided
                    if evt.avatar_url:
                        await self._component.set_avatar_for_user(
                            evt.author_id, nick, evt.avatar_url
                        )

                    # Check if this is an edit
                    is_edit = evt.raw.get("is_edit", False)
                    if is_edit:
                        # Look up original XMPP message ID
                        original_xmpp_id = self._component._msgid_tracker.get_xmpp_id(evt.message_id)
                        if original_xmpp_id:
                            await self._component.send_correction_as_user(
                                evt.author_id, muc_jid, evt.content, nick, original_xmpp_id
                            )
                        else:
                            logger.warning("Cannot send XMPP correction: original message ID not found for {}", evt.message_id)
                    else:
                        # Look up reply target XMPP message ID if replying
                        reply_to_xmpp_id = None
                        if evt.reply_to_id:
                            reply_to_xmpp_id = self._component._msgid_tracker.get_xmpp_id(evt.reply_to_id)

                        # Send new message and track ID
                        xmpp_msg_id = await self._component.send_message_as_user(
                            evt.author_id, muc_jid, evt.content, nick, reply_to_id=reply_to_xmpp_id
                        )
                        if xmpp_msg_id:
                            self._component._msgid_tracker.store(xmpp_msg_id, evt.message_id, muc_jid)

                await asyncio.sleep(0.25)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("XMPP send failed: {}", exc)

    async def start(self) -> None:
        """Start XMPP component."""
        component_jid = _get_component_jid()
        secret = _get_component_secret()
        server = _get_component_server()
        port = _get_component_port()

        if not component_jid or not secret or not server:
            logger.warning(
                "XMPP component config incomplete; XMPP adapter disabled"
            )
            return

        if not self._identity:
            logger.warning("No identity resolver; XMPP adapter disabled")
            return

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
        self._component_task = asyncio.create_task(self._component.connect())  # type: ignore[attr-defined]
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
    return os.environ.get("XMPP_COMPONENT_JID")


def _get_component_secret() -> str | None:
    return os.environ.get("XMPP_COMPONENT_SECRET")


def _get_component_server() -> str | None:
    return os.environ.get("XMPP_COMPONENT_SERVER")


def _get_component_port() -> int:
    return int(os.environ.get("XMPP_COMPONENT_PORT", "5347"))
