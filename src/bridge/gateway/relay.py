"""Relay: MessageIn -> MessageOut for other protocols (Phase 5 routing)."""

from __future__ import annotations

from bridge.events import MessageIn, message_out
from bridge.gateway.bus import Bus
from bridge.gateway.router import ChannelRouter


class Relay:
    """Relays MessageIn to MessageOut for target protocols. No adapter-to-adapter coupling."""

    TARGETS = ("discord", "irc", "xmpp")

    def __init__(self, bus: Bus, router: ChannelRouter) -> None:
        self._bus = bus
        self._router = router

    def accept_event(self, source: str, evt: object) -> bool:
        return isinstance(evt, MessageIn)

    def push_event(self, source: str, evt: object) -> None:
        if not isinstance(evt, MessageIn):
            return

        mapping = self._router.get_mapping_for_discord(evt.channel_id)
        if not mapping:
            return

        for target in self.TARGETS:
            if target == evt.origin:
                continue
            if target == "discord" and not mapping.discord_channel_id:
                continue
            if target == "irc" and not mapping.irc:
                continue
            if target == "xmpp" and not mapping.xmpp:
                continue

            channel_id = mapping.discord_channel_id
            _, out_evt = message_out(
                target_origin=target,
                channel_id=channel_id,
                author_id=evt.author_id,
                author_display=evt.author_display,
                content=evt.content,
                message_id=evt.message_id,
                reply_to_id=evt.reply_to_id,
            )
            self._bus.publish("relay", out_evt)
