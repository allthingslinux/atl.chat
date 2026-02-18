"""XMPP adapter: MUC client, join rooms, emit MessageIn; queue for outbound (AUDIT §2)."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

from loguru import logger
from slixmpp import ClientXMPP
from slixmpp.exceptions import XMPPError

from bridge.events import MessageOut, message_in
from bridge.gateway import Bus, ChannelRouter

if TYPE_CHECKING:
    from bridge.identity import IdentityResolver


class XMPPBot(ClientXMPP):
    """XMPP MUC client: joins rooms, emits MessageIn on groupchat."""

    def __init__(
        self,
        jid: str,
        password: str,
        bus: Bus,
        router: ChannelRouter,
        outbound: asyncio.Queue[MessageOut],
    ) -> None:
        super().__init__(jid, password)
        self._bus = bus
        self._router = router
        self._outbound = outbound
        self.register_plugin("xep_0030")
        self.register_plugin("xep_0045")
        self.register_plugin("xep_0199")
        self.add_event_handler("session_start", self._on_session_start)
        self.add_event_handler("groupchat_message", self._on_groupchat_message)

    async def _on_session_start(self, _: object) -> None:
        """After connect, join MUCs from mappings."""
        await self.get_roster()
        self.send_presence()
        nick = _get_xmpp_nick()
        for mapping in self._router.all_mappings():
            if mapping.xmpp:
                muc_jid = mapping.xmpp.muc_jid
                try:
                    await self.plugin["xep_0045"].join_muc(muc_jid, nick)
                    logger.info("Joined XMPP MUC: {} as {}", muc_jid, nick)
                except XMPPError as exc:
                    logger.warning("Failed to join MUC {}: {}", muc_jid, exc)

    def _on_groupchat_message(self, msg: object) -> None:
        """Handle MUC message; emit MessageIn."""
        body = (msg.get("body", "") or "") if hasattr(msg, "get") else ""
        nick = (msg.get("mucnick", "") or "") if hasattr(msg, "get") else ""
        from_jid = str(msg.get("from", "") or "") if hasattr(msg, "get") else ""
        if "/" in from_jid:
            room_jid = from_jid.split("/")[0]
            if not nick:
                nick = from_jid.split("/")[1]
        else:
            room_jid = from_jid

        mapping = self._router.get_mapping_for_xmpp(room_jid)
        if not mapping:
            return

        _, evt = message_in(
            origin="xmpp",
            channel_id=mapping.discord_channel_id,
            author_id=nick,
            author_display=nick,
            content=body,
            message_id=f"xmpp:{room_jid}:{nick}:{id(msg)}",
            is_action=False,
        )
        self._bus.publish("xmpp", evt)


class XMPPAdapter:
    """XMPP adapter: MUC client + outbound queue."""

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
        self._bot: XMPPBot | None = None
        self._consumer_task: asyncio.Task | None = None
        self._bot_task: asyncio.Task | None = None

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
        """Drain outbound queue and send to MUC."""
        while True:
            try:
                evt = await self._outbound.get()
                mapping = self._router.get_mapping_for_discord(evt.channel_id)
                if mapping and mapping.xmpp:
                    muc_jid = mapping.xmpp.muc_jid
                    if self._bot:
                        self._bot.send_message(
                            mto=muc_jid,
                            mbody=evt.content[:4000],
                            mtype="groupchat",
                        )
                await asyncio.sleep(0.25)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("XMPP send failed: {}", exc)

    async def start(self) -> None:
        """Start XMPP client."""
        jid = _get_xmpp_jid()
        password = _get_xmpp_password()
        if not jid or not password:
            logger.warning("XMPP_JID or XMPP_PASSWORD not set; XMPP adapter disabled")
            return

        mappings = self._router.all_mappings()
        xmpp_mappings = [m for m in mappings if m.xmpp]
        if not xmpp_mappings:
            logger.warning("No XMPP mappings; XMPP adapter disabled")
            return

        self._bot = XMPPBot(jid, password, self._bus, self._router, self._outbound)
        self._bus.register(self)
        self._consumer_task = asyncio.create_task(self._outbound_consumer())
        self._bot_task = asyncio.create_task(self._bot.connect_and_process())
        logger.info("XMPP client started: {}", jid)

    async def stop(self) -> None:
        """Stop XMPP client."""
        self._bus.unregister(self)
        if self._consumer_task:
            self._consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._consumer_task
        if self._bot:
            self._bot.disconnect()
        if self._bot_task:
            self._bot_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._bot_task
        self._bot = None
        self._bot_task = None


def _get_xmpp_jid() -> str | None:
    import os

    return os.environ.get("XMPP_JID")


def _get_xmpp_password() -> str | None:
    import os

    return os.environ.get("XMPP_PASSWORD")


def _get_xmpp_nick() -> str:
    import os

    return os.environ.get("XMPP_NICK", "atl-bridge")
