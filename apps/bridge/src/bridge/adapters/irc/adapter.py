"""IRC adapter: pydle-based with IRCv3 support."""

from __future__ import annotations

import asyncio
import contextlib
import os
import time
from typing import TYPE_CHECKING

from loguru import logger

from bridge.adapters.base import AdapterBase
from bridge.adapters.irc.client import IRCClient, _connect_with_backoff
from bridge.adapters.irc.msgid import MessageIDTracker, ReactionTracker
from bridge.adapters.irc.puppet import IRCPuppetManager
from bridge.config import cfg
from bridge.events import MessageDeleteOut, MessageOut, ReactionOut, TypingOut
from bridge.gateway import Bus, ChannelRouter

if TYPE_CHECKING:
    from bridge.gateway.msgid_resolver import MessageIDResolver
    from bridge.identity import IdentityResolver


class IRCAdapter(AdapterBase):
    """IRC adapter: pydle-based with IRCv3 support."""

    def __init__(
        self,
        bus: Bus,
        router: ChannelRouter,
        identity_resolver: IdentityResolver | None,
        msgid_resolver: MessageIDResolver | None = None,
    ):
        self._bus = bus
        self._router = router
        self._identity = identity_resolver
        self._client: IRCClient | None = None
        self._task: asyncio.Task | None = None
        self._puppet_manager: IRCPuppetManager | None = None
        self._puppet_tasks: set[asyncio.Task] = set()
        self._msgid_tracker = MessageIDTracker(ttl_seconds=3600)
        self._reaction_tracker = ReactionTracker(ttl_seconds=3600)
        if msgid_resolver:
            msgid_resolver.register_irc(self._msgid_tracker)

    @property
    def name(self) -> str:
        return "irc"

    def accept_event(self, source: str, evt: object) -> bool:
        """Accept MessageOut, MessageDeleteOut, ReactionOut, or TypingOut targeting IRC."""
        if isinstance(evt, MessageOut) and evt.target_origin == "irc":
            return True
        if isinstance(evt, MessageDeleteOut) and evt.target_origin == "irc":
            return True
        if isinstance(evt, ReactionOut) and evt.target_origin == "irc":
            return True
        return isinstance(evt, TypingOut) and evt.target_origin == "irc"

    def push_event(self, source: str, evt: object) -> None:
        """Queue MessageOut, MessageDeleteOut, or ReactionOut for IRC send."""
        if isinstance(evt, MessageDeleteOut) and evt.target_origin == "irc":
            if self._client:
                logger.debug(
                    "IRC: received MessageDeleteOut channel={} message_id={}",
                    evt.channel_id,
                    evt.message_id,
                )
                asyncio.create_task(self._send_redact(evt))  # noqa: RUF006
            return
        if isinstance(evt, ReactionOut) and evt.target_origin == "irc":
            if self._client:
                asyncio.create_task(self._send_reaction(evt))  # noqa: RUF006
            return
        if isinstance(evt, TypingOut) and evt.target_origin == "irc":
            if self._client:
                asyncio.create_task(self._send_typing(evt))  # noqa: RUF006
            return
        if isinstance(evt, MessageOut):
            # Use puppet if identity available, otherwise main connection
            if self._identity and self._puppet_manager:
                task = asyncio.create_task(self._send_via_puppet(evt))
                self._puppet_tasks.add(task)
                task.add_done_callback(self._puppet_tasks.discard)
            elif self._client:
                self._client.queue_message(evt)
            else:
                logger.warning("IRC MessageOut dropped: no client (channel={})", evt.channel_id)

    async def _send_reaction(self, evt: ReactionOut) -> None:
        """Send IRC TAGMSG with +draft/react for add, or +draft/unreact for removal (IRCv3 spec)."""
        if not self._client:
            return
        is_remove = evt.raw.get("is_remove", False)
        mapping = self._router.get_mapping_for_discord(evt.channel_id)
        if not mapping or not mapping.irc:
            return
        target = mapping.irc.channel

        irc_msgid = self._msgid_tracker.get_irc_msgid(evt.message_id)
        if not irc_msgid:
            logger.debug("No IRC msgid for reaction on {}; skip", evt.message_id)
            return

        if is_remove:
            try:
                await self._client.rawmsg(
                    "TAGMSG",
                    target,
                    tags={"+draft/reply": irc_msgid, "+draft/unreact": evt.emoji},
                )
                logger.info("IRC: sent reaction removal {} on message {}", evt.emoji, evt.message_id)
            except Exception as exc:
                logger.exception("Reaction unreact TAGMSG failed: {}", exc)
            return

        # Add reaction
        try:
            await self._client.rawmsg(
                "TAGMSG",
                target,
                tags={"+draft/reply": irc_msgid, "+draft/react": evt.emoji},
            )
            logger.info("IRC: sent reaction {} to channel {}", evt.emoji, target)
        except Exception as exc:
            logger.exception("Reaction TAGMSG failed: {}", exc)

    async def _send_typing(self, evt: TypingOut) -> None:
        """Send IRC TAGMSG with +typing=active for Discord typing (throttled 3s)."""
        if not self._client:
            return

        now = time.time()
        last = getattr(self._client, "_typing_last", 0)
        if now - last < 3:
            return
        self._client._typing_last = now

        mapping = self._router.get_mapping_for_discord(evt.channel_id)
        if not mapping or not mapping.irc:
            return
        target = mapping.irc.channel
        try:
            await self._client.rawmsg(
                "TAGMSG",
                target,
                tags={"typing": "active"},
            )
        except Exception as exc:
            logger.debug("Typing TAGMSG failed: {}", exc)

    async def _send_redact(self, evt: MessageDeleteOut) -> None:
        """Send REDACT to IRC when Discord message is deleted (requires draft/message-redaction)."""
        if not self._client:
            return
        if not cfg.irc_redact_enabled:
            logger.debug(
                "IRC: skipping REDACT for message {} (irc_redact_enabled=false; UnrealIRCd third/redact crashes)",
                evt.message_id,
            )
            return
        caps = getattr(self._client, "_capabilities", {})
        if not caps.get("draft/message-redaction"):
            logger.info(
                "IRC: skipping REDACT for Discord message {} (draft/message-redaction not negotiated)",
                evt.message_id,
            )
            return
        irc_msgid = self._msgid_tracker.get_irc_msgid(evt.message_id)
        if not irc_msgid:
            logger.info(
                "IRC: skipping REDACT for Discord message {} (no IRC msgid stored; echo may lack msgid tag)",
                evt.message_id,
            )
            return
        mapping = self._router.get_mapping_for_discord(evt.channel_id)
        if not mapping or not mapping.irc:
            return
        target = mapping.irc.channel
        try:
            await self._client.rawmsg("REDACT", target, irc_msgid)
            logger.info("IRC: sent REDACT for message {} to channel {}", evt.message_id, target)
            logger.debug("IRC: REDACT irc_msgid={} -> discord_id={}", irc_msgid, evt.message_id)
        except Exception as exc:
            logger.exception("REDACT failed: {}", exc)

    async def _send_via_puppet(self, evt: MessageOut):
        """Send message via puppet connection."""
        if not self._puppet_manager or not self._identity:
            return

        mapping = self._router.get_mapping_for_discord(evt.channel_id)
        if not mapping or not mapping.irc:
            return

        # Check if user has IRC identity
        has_irc = await self._identity.has_irc(evt.author_id)
        if has_irc:
            await self._puppet_manager.send_message(
                evt.author_id,
                mapping.irc.channel,
                evt.content,
                avatar_url=evt.avatar_url,
            )
        elif self._client:
            # Fallback to main connection
            self._client.queue_message(evt)

    async def start(self) -> None:
        """Start IRC connection."""
        mappings = self._router.all_mappings()
        irc_mappings = [m for m in mappings if m.irc]
        if not irc_mappings:
            logger.warning("No IRC mappings; IRC adapter disabled")
            return

        m = irc_mappings[0]
        if not m.irc:
            return

        nick = os.environ.get("BRIDGE_IRC_NICK", "atl-bridge")
        channels = list({x.irc.channel for x in irc_mappings if x.irc and x.irc.channel})

        irc_kwargs: dict = {}
        if cfg.irc_use_sasl and cfg.irc_sasl_user and cfg.irc_sasl_password:
            irc_kwargs["sasl_username"] = cfg.irc_sasl_user
            irc_kwargs["sasl_password"] = cfg.irc_sasl_password

        self._client = IRCClient(
            bus=self._bus,
            router=self._router,
            server=m.irc.server,
            nick=nick,
            channels=channels,
            msgid_tracker=self._msgid_tracker,
            reaction_tracker=self._reaction_tracker,
            throttle_limit=cfg.irc_throttle_limit,
            rejoin_delay=cfg.irc_rejoin_delay,
            auto_rejoin=cfg.irc_auto_rejoin,
            **irc_kwargs,
        )

        self._bus.register(self)

        self._task = asyncio.create_task(
            _connect_with_backoff(
                self._client,
                hostname=m.irc.server,
                port=m.irc.port,
                tls=m.irc.tls,
                tls_verify=cfg.irc_tls_verify,
            )
        )

        # Start puppet manager if identity resolver available
        if self._identity:
            idle_timeout = int(os.environ.get("IRC_PUPPET_IDLE_TIMEOUT_HOURS", "24"))
            self._puppet_manager = IRCPuppetManager(
                bus=self._bus,
                router=self._router,
                identity=self._identity,
                server=m.irc.server,
                port=m.irc.port,
                tls=m.irc.tls,
                tls_verify=cfg.irc_tls_verify,
                idle_timeout_hours=idle_timeout,
                ping_interval=cfg.irc_puppet_ping_interval,
                prejoin_commands=cfg.irc_puppet_prejoin_commands,
            )
            pm = self._puppet_manager
            await pm.start()
            logger.info("IRC puppet manager started (idle timeout: {}h)", idle_timeout)
            # Main connection receives puppet PRIVMSGs; skip to prevent Discord echo
            self._client._puppet_nick_check = lambda n, m=pm: n in m.get_puppet_nicks()

        logger.info(
            "IRC connection started: {}:{}, channels {}",
            m.irc.server,
            m.irc.port,
            channels,
        )

    async def stop(self) -> None:
        """Stop IRC connection."""
        self._bus.unregister(self)
        if self._puppet_manager:
            await self._puppet_manager.stop()
        if self._client:
            await self._client.disconnect()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._client = None
        self._task = None
        self._puppet_manager = None
