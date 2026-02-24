"""Relay: MessageIn -> MessageOut for other protocols (Phase 5 routing)."""

from __future__ import annotations

import re

from bridge.config import cfg
from bridge.events import (
    MessageDelete,
    MessageIn,
    ReactionIn,
    TypingIn,
    message_delete_out,
    message_out,
    reaction_out,
    typing_out,
)
from bridge.formatting.discord_to_irc import discord_to_irc
from bridge.formatting.irc_to_discord import irc_to_discord
from bridge.gateway.bus import Bus
from bridge.gateway.router import ChannelRouter


def _transform_content(content: str, origin: str, target: str) -> str:
    """Transform content for target protocol based on origin."""
    if target == "irc" and origin == "discord":
        return discord_to_irc(content)
    if target == "discord" and origin == "irc":
        return irc_to_discord(content)
    return content


def _content_matches_filter(content: str) -> bool:
    """Return True if content matches any content_filter_regex pattern."""
    patterns = cfg.content_filter_regex
    if not patterns:
        return False
    for pat in patterns:
        try:
            if re.search(pat, content):
                return True
        except re.error:
            continue
    return False


class Relay:
    """Relays MessageIn to MessageOut for target protocols. No adapter-to-adapter coupling."""

    TARGETS = ("discord", "irc", "xmpp")

    def __init__(self, bus: Bus, router: ChannelRouter) -> None:
        self._bus = bus
        self._router = router

    def accept_event(self, source: str, evt: object) -> bool:
        return isinstance(evt, (MessageIn, MessageDelete, ReactionIn, TypingIn))

    def push_event(self, source: str, evt: object) -> None:
        if isinstance(evt, MessageDelete):
            self._push_message_delete(evt)
            return
        if isinstance(evt, ReactionIn):
            self._push_reaction(evt)
            return
        if isinstance(evt, TypingIn):
            self._push_typing(evt)
            return
        if not isinstance(evt, MessageIn):
            return

        # Skip if content matches filter
        if _content_matches_filter(evt.content):
            return

        # Look up mapping based on origin
        mapping = None
        if evt.origin == "discord":
            mapping = self._router.get_mapping_for_discord(evt.channel_id)
        elif evt.origin == "irc":
            # Parse IRC channel_id format: "server/channel"
            parts = evt.channel_id.split("/", 1)
            if len(parts) == 2:
                mapping = self._router.get_mapping_for_irc(parts[0], parts[1])
        elif evt.origin == "xmpp":
            mapping = self._router.get_mapping_for_xmpp(evt.channel_id)

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
            content = _transform_content(evt.content, evt.origin, target)
            _, out_evt = message_out(
                target_origin=target,
                channel_id=channel_id,
                author_id=evt.author_id,
                author_display=evt.author_display,
                content=content,
                message_id=evt.message_id,
                reply_to_id=evt.reply_to_id,
                avatar_url=evt.avatar_url,
                raw={
                    "is_edit": evt.is_edit,
                    "replace_id": evt.raw.get("replace_id"),
                    "origin": evt.origin,
                    "xmpp_id_aliases": evt.raw.get("xmpp_id_aliases", []),
                },
            )
            self._bus.publish("relay", out_evt)

    def _push_reaction(self, evt: ReactionIn) -> None:
        """Route ReactionIn to IRC and XMPP."""
        mapping = None
        if evt.origin == "discord":
            mapping = self._router.get_mapping_for_discord(evt.channel_id)
        elif evt.origin == "irc":
            parts = evt.channel_id.split("/", 1)
            if len(parts) == 2:
                mapping = self._router.get_mapping_for_irc(parts[0], parts[1])
        elif evt.origin == "xmpp":
            mapping = self._router.get_mapping_for_xmpp(evt.channel_id)
        if not mapping:
            return
        channel_id = mapping.discord_channel_id
        for target in self.TARGETS:
            if target == evt.origin:
                continue
            if target == "irc" and not mapping.irc:
                continue
            if target == "xmpp" and not mapping.xmpp:
                continue
            if target == "discord" and not mapping.discord_channel_id:
                continue
            _, out_evt = reaction_out(
                target_origin=target,
                channel_id=channel_id,
                message_id=evt.message_id,
                emoji=evt.emoji,
                author_id=evt.author_id,
                author_display=evt.author_display,
                raw=evt.raw,
            )
            self._bus.publish("relay", out_evt)

    def _push_typing(self, evt: TypingIn) -> None:
        """Route TypingIn to IRC and Discord."""
        mapping = None
        if evt.origin == "discord":
            mapping = self._router.get_mapping_for_discord(evt.channel_id)
        elif evt.origin == "irc":
            parts = evt.channel_id.split("/", 1)
            if len(parts) == 2:
                mapping = self._router.get_mapping_for_irc(parts[0], parts[1])
        elif evt.origin == "xmpp":
            mapping = self._router.get_mapping_for_xmpp(evt.channel_id)
        if not mapping:
            return
        channel_id = mapping.discord_channel_id
        for target in self.TARGETS:
            if target == evt.origin:
                continue
            if target == "irc" and not mapping.irc:
                continue
            if target == "xmpp" and not mapping.xmpp:
                continue
            if target == "discord" and not mapping.discord_channel_id:
                continue
            _, out_evt = typing_out(target_origin=target, channel_id=channel_id)
            self._bus.publish("relay", out_evt)

    def _push_message_delete(self, evt: MessageDelete) -> None:
        """Route MessageDelete to IRC and XMPP for REDACT/retraction."""
        mapping = None
        if evt.origin == "discord":
            mapping = self._router.get_mapping_for_discord(evt.channel_id)
        elif evt.origin == "irc":
            parts = evt.channel_id.split("/", 1)
            if len(parts) == 2:
                mapping = self._router.get_mapping_for_irc(parts[0], parts[1])
        elif evt.origin == "xmpp":
            mapping = self._router.get_mapping_for_xmpp(evt.channel_id)

        if not mapping:
            return

        channel_id = mapping.discord_channel_id
        for target in self.TARGETS:
            if target == evt.origin:
                continue
            if target == "irc" and not mapping.irc:
                continue
            if target == "xmpp" and not mapping.xmpp:
                continue
            if target == "discord" and not mapping.discord_channel_id:
                continue
            _, out_evt = message_delete_out(
                target_origin=target,
                channel_id=channel_id,
                message_id=evt.message_id,
                author_id=evt.author_id,
            )
            self._bus.publish("relay", out_evt)
