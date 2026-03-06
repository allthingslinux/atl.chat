"""Relay: MessageIn -> MessageOut for other protocols (Phase 5 routing)."""

from __future__ import annotations

import re
from collections.abc import Callable

from loguru import logger

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
from bridge.formatting.converter import convert
from bridge.gateway.bus import Bus
from bridge.gateway.pipeline import Pipeline, TransformContext
from bridge.gateway.router import ChannelMapping, ChannelRouter
from bridge.gateway.steps import (
    add_reply_fallback,
    format_convert,
    strip_invalid_xml,
    strip_reply_fallback,
    unwrap_spoiler,
    wrap_spoiler,
)

# Protocols that support native message editing — no edit suffix needed.
# IRC has no edit mechanism, so edited messages get an " (edited)" suffix appended.
# Discord uses webhook_edit and XMPP uses XEP-0308 Last Message Correction.
_NATIVE_EDIT_PROTOCOLS: frozenset[str] = frozenset({"discord", "xmpp"})


def _transform_content(content: str, origin: str, target: str) -> str:
    """Transform content for target protocol based on origin.

    Backward-compatible shim — delegates to the IR-based converter.
    """
    return convert(content, origin, target)


_compiled_filters: list[re.Pattern[str]] = []


def _build_content_filters(patterns: list[str]) -> list[re.Pattern[str]]:
    """Pre-compile regex patterns. Invalid patterns are logged and skipped."""
    compiled = []
    for pat in patterns:
        try:
            compiled.append(re.compile(pat))
        except re.error as exc:
            logger.warning("Invalid content_filter_regex '{}': {}", pat, exc)
    return compiled


def rebuild_content_filters() -> None:
    """Rebuild compiled content filters from config. Called on config load/reload."""
    global _compiled_filters  # noqa: PLW0603
    _compiled_filters = _build_content_filters(cfg.content_filter_regex)


def _content_matches_filter(content: str) -> bool:
    """Return True if content matches any pre-compiled content_filter_regex pattern."""
    return any(pat.search(content) for pat in _compiled_filters)


def _lazy_content_filter(content: str, ctx: TransformContext) -> str | None:
    """Content filter step that reads from the module-level ``_compiled_filters``.

    Uses module-level state instead of closure-captured patterns so that
    filters can be rebuilt (e.g. on config reload or in tests) without
    reconstructing the entire pipeline object.
    """
    if not content:
        return content  # empty → pass through unchanged
    for pat in _compiled_filters:
        if pat.search(content):
            return None  # drop
    return content


def _build_default_pipeline() -> Pipeline:
    """Build the default content transformation pipeline (Design §D6).

    Steps in declared order:
    1. strip_reply_fallback  — remove origin-protocol reply quotes before conversion
    2. unwrap_spoiler        — extract spoiler markers into ctx.spoiler flag
    3. format_convert        — IR-based cross-protocol formatting conversion
    4. wrap_spoiler          — re-apply spoiler in target-protocol syntax
    5. strip_invalid_xml     — remove chars illegal in XML 1.0 (XMPP targets only)
    6. add_reply_fallback    — prepend "> quote | reply" for IRC targets
    7. content_filter        — drop messages matching configured regex patterns

    Order matters: spoiler must be unwrapped before format conversion so the
    converter sees clean text, and re-wrapped after so the target gets the
    correct spoiler syntax. strip_invalid_xml runs between wrap_spoiler and
    add_reply_fallback because the reply fallback itself is plain ASCII.
    """
    return Pipeline(
        [
            strip_reply_fallback,
            unwrap_spoiler,
            format_convert,
            wrap_spoiler,
            strip_invalid_xml,
            add_reply_fallback,
            _lazy_content_filter,
        ]
    )


class Relay:
    """Relays MessageIn to MessageOut for target protocols. No adapter-to-adapter coupling."""

    TARGETS = ("discord", "irc", "xmpp")

    def __init__(self, bus: Bus, router: ChannelRouter) -> None:
        self._bus = bus
        self._router = router
        rebuild_content_filters()
        self._pipeline = _build_default_pipeline()

    def _get_mapping_for_origin(
        self, origin: str, channel_id: str, *, fallback_discord: bool = False
    ) -> ChannelMapping | None:
        """Resolve channel mapping from origin and channel_id.

        IRC: channel_id is "server/channel"; optionally fallback to discord lookup (tests).
        """
        if origin == "discord":
            return self._router.get_mapping_for_discord(channel_id)
        if origin == "irc":
            parts = channel_id.split("/", 1)
            if len(parts) == 2:
                mapping = self._router.get_mapping_for_irc(parts[0], parts[1])
                if mapping:
                    return mapping
            if fallback_discord:
                return self._router.get_mapping_for_discord(channel_id)
            return None
        if origin == "xmpp":
            return self._router.get_mapping_for_xmpp(channel_id)
        return None

    def _emit_targets(
        self,
        mapping: ChannelMapping,
        origin: str,
        emit_fn: Callable[[str], object],
    ) -> None:
        """Call emit_fn(target) for each target protocol that should receive the event."""
        for target in self.TARGETS:
            if target == origin:
                continue
            if target == "irc" and not mapping.irc:
                continue
            if target == "xmpp" and not mapping.xmpp:
                continue
            if target == "discord" and not mapping.discord_channel_id:
                continue
            evt = emit_fn(target)
            if evt is not None:
                self._bus.publish("relay", evt)

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

        mapping = self._get_mapping_for_origin(evt.origin, evt.channel_id, fallback_discord=True)
        if not mapping:
            logger.warning("Relay: no mapping for {} channel {}", evt.origin, evt.channel_id)
            return

        channel_id = mapping.discord_channel_id

        def emit_message(target: str) -> object:
            logger.info("Relay: {} -> {} channel={}", evt.origin, target, channel_id)

            # Build TransformContext from event fields
            ctx = TransformContext(
                origin=evt.origin,
                target=target,
                is_edit=evt.is_edit,
                reply_to_id=evt.reply_to_id,
                raw={
                    "reply_quoted_content": evt.raw.get("reply_quoted_content"),
                    "reply_quoted_author": evt.raw.get("reply_quoted_author"),
                    "unstyled": evt.raw.get("unstyled"),
                },
            )

            # Run the pipeline
            content = self._pipeline.transform(evt.content, ctx)
            if content is None:
                return None  # message dropped by content filter

            # Edit suffix: append when target doesn't support native edits
            if evt.is_edit and target not in _NATIVE_EDIT_PROTOCOLS:
                suffix = cfg.edit_suffix
                if suffix:
                    content += suffix

            out_raw = {
                "is_edit": evt.is_edit,
                "replace_id": evt.raw.get("replace_id"),
                "origin": evt.origin,
                "xmpp_id_aliases": evt.raw.get("xmpp_id_aliases", []),
            }
            # Pass through media dimensions for XEP-0446 file metadata
            if evt.raw.get("media_width"):
                out_raw["media_width"] = evt.raw["media_width"]
                out_raw["media_height"] = evt.raw["media_height"]
            # Propagate reply_fallback_added from pipeline context
            if ctx.raw.get("reply_fallback_added"):
                out_raw["reply_fallback_added"] = True
            _, out_evt = message_out(
                target_origin=target,
                channel_id=channel_id,
                author_id=evt.author_id,
                author_display=evt.author_display,
                content=content,
                message_id=evt.message_id,
                reply_to_id=evt.reply_to_id,
                is_action=evt.is_action,
                avatar_url=evt.avatar_url,
                raw=out_raw,
            )
            logger.debug(
                "Relay: emitting MessageOut target={} author={} content={!r}",
                target,
                evt.author_display,
                content[:80],
            )
            return out_evt

        self._emit_targets(mapping, evt.origin, emit_message)

    def _push_reaction(self, evt: ReactionIn) -> None:
        """Route ReactionIn to IRC and XMPP."""
        mapping = self._get_mapping_for_origin(evt.origin, evt.channel_id)
        if not mapping:
            logger.debug("Relay: no mapping for reaction from {} channel {}", evt.origin, evt.channel_id)
            return

        def emit(target: str) -> object:
            logger.debug(
                "Relay: reaction {} -> {} emoji={} author={}", evt.origin, target, evt.emoji, evt.author_display
            )
            _, out_evt = reaction_out(
                target_origin=target,
                channel_id=mapping.discord_channel_id,
                message_id=evt.message_id,
                emoji=evt.emoji,
                author_id=evt.author_id,
                author_display=evt.author_display,
                raw=evt.raw,
            )
            return out_evt

        self._emit_targets(mapping, evt.origin, emit)

    def _push_typing(self, evt: TypingIn) -> None:
        """Route TypingIn to IRC and Discord."""
        mapping = self._get_mapping_for_origin(evt.origin, evt.channel_id)
        if not mapping:
            return

        def emit(target: str) -> object:
            _, out_evt = typing_out(target_origin=target, channel_id=mapping.discord_channel_id)
            return out_evt

        self._emit_targets(mapping, evt.origin, emit)

    def _push_message_delete(self, evt: MessageDelete) -> None:
        """Route MessageDelete to IRC and XMPP for REDACT/retraction."""
        mapping = self._get_mapping_for_origin(evt.origin, evt.channel_id)
        if not mapping:
            logger.debug("Relay: no mapping for delete from {} channel {}", evt.origin, evt.channel_id)
            return

        logger.info("Relay: delete {} -> all targets message_id={}", evt.origin, evt.message_id)

        def emit(target: str) -> object:
            logger.debug("Relay: emitting MessageDeleteOut target={} message_id={}", target, evt.message_id)
            _, out_evt = message_delete_out(
                target_origin=target,
                channel_id=mapping.discord_channel_id,
                message_id=evt.message_id,
                author_id=evt.author_id,
                author_display=evt.author_display,
            )
            return out_evt

        self._emit_targets(mapping, evt.origin, emit)
