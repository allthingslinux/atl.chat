"""Unified message ID resolver for cross-protocol message correlation.

Thin wrapper over BidirectionalTTLMap that maintains one map per protocol
pair and provides protocol-specific convenience methods for storing and
resolving origin_id ↔ target_id mappings.

Replaces the duplicated implementations in adapters/irc/msgid.py and
adapters/xmpp/msgid.py (Requirements 7.1, 7.2, 7.3).
"""

from __future__ import annotations

from typing import Any

from bridge.core.constants import ProtocolOrigin
from bridge.tracking.base import BidirectionalTTLMap

# Pair key is the tuple used to index into the per-pair map dict.
# We always store the first-seen ordering and swap lookups when the
# caller uses the reversed pair.
_PairKey = tuple[ProtocolOrigin, ProtocolOrigin]


class MessageIDResolver:
    """Resolve message IDs across protocol boundaries.

    Maintains a ``BidirectionalTTLMap`` per protocol pair so that
    ``store("discord", "irc", discord_id, irc_msgid)`` followed by
    ``resolve("discord", "irc", discord_id)`` returns ``irc_msgid``,
    and ``resolve_reverse("discord", "irc", irc_msgid)`` returns
    ``discord_id``.

    The pair ordering is canonical — ``("discord", "irc")`` and
    ``("irc", "discord")`` share the same underlying map. The first
    call to access a pair establishes the canonical ordering; subsequent
    calls with the reversed pair detect the swap and adjust lookups
    accordingly.
    """

    def __init__(
        self,
        ttl_seconds: int = 3600,
        maxsize: int = 10_000,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._maxsize = maxsize
        self._maps: dict[_PairKey, BidirectionalTTLMap[str, Any]] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_map_and_swapped(
        self,
        protocol_a: ProtocolOrigin,
        protocol_b: ProtocolOrigin,
    ) -> tuple[BidirectionalTTLMap[str, Any], bool]:
        """Return the map for the pair and whether the caller's order is swapped.

        On first access for a given pair the map is created with the
        caller's ordering as canonical (``swapped=False``).
        """
        key: _PairKey = (protocol_a, protocol_b)
        if key in self._maps:
            return self._maps[key], False

        rev_key: _PairKey = (protocol_b, protocol_a)
        if rev_key in self._maps:
            return self._maps[rev_key], True

        # First access — create with caller's ordering as canonical.
        m: BidirectionalTTLMap[str, Any] = BidirectionalTTLMap(
            ttl_seconds=self._ttl_seconds,
            maxsize=self._maxsize,
        )
        self._maps[key] = m
        return m, False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(
        self,
        origin_protocol: ProtocolOrigin,
        target_protocol: ProtocolOrigin,
        origin_id: str,
        target_id: str,
        value: Any = None,
    ) -> None:
        """Store a bidirectional mapping between *origin_id* and *target_id*.

        The mapping is keyed by the protocol pair so that later
        ``resolve`` / ``resolve_reverse`` calls with the same pair
        (in either order) find the entry.
        """
        m, swapped = self._get_map_and_swapped(origin_protocol, target_protocol)
        if swapped:
            # The canonical map has the reversed pair ordering, so
            # origin_id goes into the *reverse* side.
            m.store(target_id, origin_id, value)
        else:
            m.store(origin_id, target_id, value)

    def resolve(
        self,
        origin_protocol: ProtocolOrigin,
        target_protocol: ProtocolOrigin,
        origin_id: str,
    ) -> str | None:
        """Look up the *target_id* that was stored for *origin_id*.

        Returns ``None`` when no mapping exists or the entry has expired.
        """
        m, swapped = self._get_map_and_swapped(origin_protocol, target_protocol)
        result = m.get_reverse(origin_id) if swapped else m.get_forward(origin_id)
        if result is None:
            return None
        target_id, _value = result
        return target_id

    def resolve_reverse(
        self,
        origin_protocol: ProtocolOrigin,
        target_protocol: ProtocolOrigin,
        target_id: str,
    ) -> str | None:
        """Look up the *origin_id* that was stored for *target_id*.

        This is the reverse of ``resolve``: given a target-side message
        ID, return the origin-side message ID.

        Returns ``None`` when no mapping exists or the entry has expired.
        """
        m, swapped = self._get_map_and_swapped(origin_protocol, target_protocol)
        result = m.get_forward(target_id) if swapped else m.get_reverse(target_id)
        if result is None:
            return None
        origin_id, _value = result
        return origin_id
