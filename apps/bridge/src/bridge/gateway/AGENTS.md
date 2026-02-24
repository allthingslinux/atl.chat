# Gateway

> Scope: `src/bridge/gateway/` — inherits root [AGENTS.md](../../../AGENTS.md).

Central event routing layer. No protocol-specific logic lives here.

## Files

| File | Purpose |
|------|---------|
| `bus.py` | `Bus` — thin wrapper around `Dispatcher`; registers adapters, publishes events |
| `relay.py` | `Relay` — routes `MessageIn` → `MessageOut` (and delete/reaction/typing) for all target protocols |
| `router.py` | `ChannelRouter` — maps Discord channel IDs ↔ IRC server/channel ↔ XMPP MUC JID |

## Bus (`bus.py`)

Wraps `events.Dispatcher`. All adapters register here; the Bus is the only way events cross adapter boundaries.

- `Bus.register(target)` / `Bus.unregister(target)` — add/remove at runtime
- `Bus.publish(source, evt)` — calls `accept_event` then `push_event` on each registered target; exceptions are caught and logged per-target so one bad adapter can't block others

## Relay (`relay.py`)

Registered on the Bus as an `EventTarget`. Accepts `MessageIn`, `MessageDelete`, `ReactionIn`, `TypingIn`.

For each inbound event:
1. Looks up the `ChannelMapping` via `ChannelRouter` based on origin (`discord` / `irc` / `xmpp`)
2. For IRC channel IDs, parses `"server/channel"` format
3. Skips if no mapping found or content matches `cfg.content_filter_regex`
4. Emits a corresponding `*Out` event for every other protocol in the mapping via `Bus.publish("relay", out_evt)`

Format conversion applied by `_transform_content`:
- `discord` → `irc`: `discord_to_irc()`
- `irc` → `discord`: `irc_to_discord()`
- All other pairs: content passed through unchanged

`MessageOut.raw` carries `{"is_edit": bool, "replace_id": str|None, "origin": str}` for downstream adapters.
`ReactionOut.raw` is forwarded verbatim from `ReactionIn.raw` (preserves `is_remove` flag).

## Router (`router.py`)

`ChannelRouter` is built from the `mappings` list in config via `load_from_config(cfg.raw)`.

Dataclasses:
- `IrcTarget(server, port, tls, channel)` — IRC side of a mapping
- `XmppTarget(muc_jid)` — XMPP side of a mapping
- `ChannelMapping(discord_channel_id, irc, xmpp)` — one full mapping; `irc` or `xmpp` may be `None`

Lookup methods (all return `None` if not found — callers must handle):
- `get_mapping_for_discord(channel_id)`
- `get_mapping_for_irc(server, channel)`
- `get_mapping_for_xmpp(muc_jid)`
- `all_mappings()` — full list, used by adapters at startup to determine which protocols are active

## Related

- [Root AGENTS.md](../../../AGENTS.md)
- [adapters/AGENTS.md](../adapters/AGENTS.md)
- [formatting/AGENTS.md](../formatting/AGENTS.md)
- [bridge/AGENTS.md](../AGENTS.md)
