# bridge

> Scope: `src/bridge/` — inherits root [AGENTS.md](../../AGENTS.md).

The `bridge` Python package. Entry point, config, events, and identity live here. Protocol logic lives in subdirs.

## Files

| File | Purpose |
|------|---------|
| `__main__.py` | Arg parsing, logging setup, SIGHUP reload, uvloop/asyncio run, adapter wiring |
| `config.py` | `Config` class — YAML load, dotenv overlay, attribute accessors; `cfg` global singleton |
| `events.py` | All event dataclasses, factory functions, `Dispatcher`, `EventTarget` protocol |
| `identity.py` | `PortalClient` (httpx + tenacity) + `IdentityResolver` (TTLCache wrapper) |

## Startup Sequence

1. Parse args (`--config`, `--verbose`, `--version`)
2. `setup_logging()` — loguru to stderr, DEBUG if `--verbose`
3. `reload_config(path)` — loads YAML + dotenv, updates `cfg` global
4. Register `SIGHUP` handler — calls `reload_config` + dispatches `ConfigReload` event
5. Create `Bus`, `ChannelRouter` (loaded from `cfg.raw`), `Relay` (registered on Bus)
6. Optionally create `PortalClient` + `IdentityResolver` if `PORTAL_BASE_URL` is set
7. Start `DiscordAdapter`, `IRCAdapter`, `XMPPAdapter`
8. `uvloop.run()` on Linux/macOS, `asyncio.run()` fallback; sleeps until `CancelledError`
9. On shutdown: `stop()` called on all adapters in order

## Event System (`events.py`)

All events are dataclasses. Factory functions (decorated with `@event`) return `(type_name, instance)` tuples.

| Dataclass | Factory | Direction |
|-----------|---------|-----------|
| `MessageIn` | `message_in()` | Inbound from any protocol |
| `MessageOut` | `message_out()` | Outbound to a specific protocol |
| `MessageDelete` | `message_delete()` | Inbound delete |
| `MessageDeleteOut` | `message_delete_out()` | Outbound delete (REDACT / retraction) |
| `ReactionIn` | `reaction_in()` | Inbound reaction |
| `ReactionOut` | `reaction_out()` | Outbound reaction |
| `TypingIn` | `typing_in()` | Inbound typing indicator |
| `TypingOut` | `typing_out()` | Outbound typing indicator |
| `Join` | `join()` | User joined channel |
| `Part` | `part()` | User left channel |
| `Quit` | `quit()` | User disconnected |
| `ConfigReload` | `config_reload()` | SIGHUP config reload signal |

`Dispatcher` (and the `dispatcher` singleton) calls `accept_event` then `push_event` on each registered `EventTarget`. Exceptions per-target are caught and logged — one bad adapter can't block others.

`MessageIn` notable fields: `is_edit`, `is_action`, `reply_to_id`, `avatar_url`, `raw`.
`MessageOut` notable fields: `reply_to_id`, `avatar_url`, `raw` (carries `is_edit`, `replace_id`, `origin`).

## Config (`config.py`)

`Config.reload(data)` hot-swaps config on SIGHUP without restart. `cfg` is the global singleton — never instantiate a second `Config`.

Full property reference (see root AGENTS.md for the table). Additional properties not in root table:

| Property | Default | Description |
|----------|---------|-------------|
| `announce_extras` | `false` | Relay topic/mode changes |
| `identity_cache_ttl_seconds` | 3600 | TTL for identity cache |
| `avatar_cache_ttl_seconds` | 86400 | TTL for avatar URL cache |
| `irc_throttle_limit` | 10 | IRC messages per second (token bucket) |
| `irc_message_queue` | 30 | Max IRC outbound queue size |
| `irc_rejoin_delay` | 5 | Seconds before rejoin after KICK/disconnect |
| `irc_auto_rejoin` | `true` | Auto-rejoin channels after KICK/disconnect |
| `irc_use_sasl` | `false` | Use SASL PLAIN for IRC auth |
| `irc_sasl_user` | `""` | SASL username |
| `irc_sasl_password` | `""` | SASL password |

## Identity (`identity.py`)

`PortalClient` retries on transient HTTP errors (5 attempts, exponential backoff 2–30s via tenacity). Returns `None` on 404 — never raises for missing identity.

`IdentityResolver` wraps the client with a `TTLCache` (default 1h). Supported directions:
- `discord_to_irc(discord_id)` → IRC nick or `None`
- `discord_to_xmpp(discord_id)` → XMPP JID or `None`
- `irc_to_discord(nick, server?)` → Discord ID or `None`
- `xmpp_to_discord(jid)` → Discord ID or `None`
- `has_irc(discord_id)` / `has_xmpp(discord_id)` → bool convenience helpers

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `PORTAL_BASE_URL` / `PORTAL_URL` | Portal API base URL (identity resolution) |
| `PORTAL_TOKEN` / `PORTAL_API_TOKEN` | Bearer token for Portal API |
| `DISCORD_TOKEN` | Discord bot token |
| `IRC_NICK` | Main IRC connection nick (default: `atl-bridge`) |
| `XMPP_COMPONENT_JID` | XMPP component JID |
| `XMPP_COMPONENT_SECRET` | XMPP component secret |
| `XMPP_COMPONENT_SERVER` | XMPP server hostname |
| `XMPP_COMPONENT_PORT` | XMPP component port (default: `5347`) |

## Related

- [gateway/AGENTS.md](gateway/AGENTS.md) — Bus, Relay, Router
- [adapters/AGENTS.md](adapters/AGENTS.md) — Discord, IRC, XMPP adapters
- [formatting/AGENTS.md](formatting/AGENTS.md) — Format converters
- [Root AGENTS.md](../../AGENTS.md)
