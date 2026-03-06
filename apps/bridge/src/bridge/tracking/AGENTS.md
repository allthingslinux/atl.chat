# Tracking

> Scope: `src/bridge/tracking/` -- inherits [Bridge AGENTS.md](../../../AGENTS.md).

Cross-protocol message correlation. Maps message IDs between Discord, IRC, and XMPP so edits, deletions, and reactions can target the correct message on each protocol.

## Files

| File | Purpose |
|------|---------|
| `base.py` | `BidirectionalTTLMap` -- generic bidirectional TTL cache; entries expire after a configurable TTL; supports forward and reverse lookup |
| `message_ids.py` | `MessageIDResolver` -- per-protocol-pair ID mapping built on `BidirectionalTTLMap`; resolves e.g. Discord message ID → XMPP stanza ID |

## BidirectionalTTLMap (`base.py`)

Generic `BidirectionalTTLMap[K, V]`:

- `put(key, value)` -- stores both `key→value` and `value→key` with a timestamp
- `get(key)` -- forward lookup (returns `None` if expired or missing)
- `reverse(value)` -- reverse lookup
- Expired entries are lazily pruned on access

## MessageIDResolver (`message_ids.py`)

Wraps multiple `BidirectionalTTLMap` instances, one per protocol pair (discord↔irc, discord↔xmpp, irc↔xmpp). Used by adapters to find the target-protocol message ID when processing edits, deletions, and reactions.

## Related

- [gateway/AGENTS.md](../gateway/AGENTS.md)
- [bridge/AGENTS.md](../AGENTS.md)
- [Bridge AGENTS.md](../../../AGENTS.md)
