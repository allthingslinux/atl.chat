"""Generic bidirectional TTL map.

Replaces the duplicated _cleanup() pattern in irc/msgid.py and xmpp/msgid.py
with a single, tested, generic implementation.
"""

import time
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class TTLEntry(Generic[V]):
    """A value paired with its creation timestamp."""

    __slots__ = ("timestamp", "value")

    def __init__(self, value: V, timestamp: float) -> None:
        self.value = value
        self.timestamp = timestamp


class BidirectionalTTLMap(Generic[K, V]):
    """Bidirectional mapping with automatic TTL expiry.

    Maps key1 ↔ key2 with an associated value and timestamp.
    Supports forward lookup (key1 → key2, value) and reverse lookup
    (key2 → key1, value), plus alias resolution.
    """

    def __init__(self, ttl_seconds: int = 3600, maxsize: int = 10000) -> None:
        self._ttl = ttl_seconds
        self._maxsize = maxsize
        self._forward: dict[K, TTLEntry[tuple[K, V]]] = {}
        self._reverse: dict[K, TTLEntry[tuple[K, V]]] = {}

    def store(self, key1: K, key2: K, value: V | None = None) -> None:
        """Store a bidirectional mapping between key1 and key2."""
        self._evict_if_full()
        entry = TTLEntry((key2, value), time.time())
        self._forward[key1] = entry
        self._reverse[key2] = TTLEntry((key1, value), entry.timestamp)

    def get_forward(self, key1: K) -> tuple[K, V] | None:
        """Look up key1 → (key2, value). Returns None if missing or expired."""
        self._cleanup()
        entry = self._forward.get(key1)
        return entry.value if entry else None

    def get_reverse(self, key2: K) -> tuple[K, V] | None:
        """Look up key2 → (key1, value). Returns None if missing or expired."""
        self._cleanup()
        entry = self._reverse.get(key2)
        return entry.value if entry else None

    def add_alias(self, alias: K, primary: K, *, forward: bool = True) -> bool:
        """Add an alias that resolves to the same entry as primary.

        Args:
            alias: The new key to add.
            primary: An existing key whose entry the alias should share.
            forward: If True, alias is added to the forward store;
                     if False, to the reverse store.

        Returns:
            True if the alias was added, False if primary doesn't exist.
        """
        store = self._forward if forward else self._reverse
        entry = store.get(primary)
        if not entry:
            return False
        store[alias] = entry
        return True

    def _cleanup(self) -> None:
        """Remove all entries whose TTL has expired."""
        cutoff = time.time() - self._ttl
        for store in (self._forward, self._reverse):
            expired = [k for k, e in store.items() if e.timestamp < cutoff]
            for k in expired:
                del store[k]

    def _evict_if_full(self) -> None:
        """If the forward store is at capacity, run cleanup to free space."""
        if len(self._forward) >= self._maxsize:
            self._cleanup()
