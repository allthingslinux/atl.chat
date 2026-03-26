# ATL Bridge

> Scope: Root project (applies to all subdirectories unless overridden)

Production-ready Discord-IRC-XMPP bridge with multi-presence and Portal identity.

## Quick Facts

- **Language:** Python 3.10+
- **Package Manager:** uv (never pip directly)
- **Key Commands:** `just bridge check`, `just bridge test`, `just bridge rebuild`, `just bridge lint`, `just bridge format`, `just bridge typecheck` (from monorepo root)
- **Entry Point:** `uv run bridge --config config.yaml`

## Tech Stack

discord.py · pydle (IRC) · slixmpp (XMPP) · asyncio · uvloop · loguru · tenacity · httpx · pyyaml · basedpyright · ruff · hypothesis (property-based testing)

## Architecture

Event-driven: all protocol adapters communicate through a central `Bus`. No adapter talks directly to another. Formatting uses an intermediate representation (IR) for lossless cross-protocol conversion.

```
Discord Adapter  --+
IRC Adapter      ---->  Bus -> Relay -> Pipeline -> Bus -> target adapters
XMPP Adapter     --+
```

- **Bus** (`gateway/bus.py`) -- dispatches typed events to registered adapters
- **Relay** (`gateway/relay.py`) -- transforms `MessageIn` -> `MessageOut` for other protocols
- **Pipeline** (`gateway/pipeline.py`, `gateway/steps.py`) -- composable transform steps (spoiler, reply fallback, content filter, format conversion)
- **Router** (`gateway/router.py`) -- maps Discord channel IDs <-> IRC channels <-> XMPP MUCs
- **Identity** (`identity/`) -- Portal API client with TTL cache; resolves Discord ID -> IRC nick / XMPP JID
- **Tracking** (`tracking/`) -- BidirectionalTTLMap and MessageIDResolver for cross-protocol message correlation
- **Formatting** (`formatting/`) -- IR-based format conversion: primitives, markdown parser/emitter, IRC codes, XEP-0393/0394, converter registry

## Repository Structure

```
src/bridge/
├── __main__.py          # Entry point + signal handling
├── avatar.py            # Avatar URL caching and resolution
├── events.py            # Re-export from core.events
├── errors.py            # Re-export from core.errors
├── config/              # YAML config + env overlay
│   ├── loader.py        # load_config, validate_config, load_config_with_env
│   └── schema.py        # Config class, cfg singleton
├── core/                # Domain primitives
│   ├── constants.py     # ProtocolOrigin, ORIGINS
│   ├── events.py        # Event dataclasses, factories, Dispatcher, BridgeAdapter
│   └── errors.py        # BridgeError, BridgeConfigurationError
├── identity/            # Portal API + dev resolver + sanitization
│   ├── base.py          # IdentityResolver ABC, DevIdentityResolver
│   ├── portal.py        # PortalClient, PortalIdentityResolver
│   ├── dev.py           # DevIdentityResolver (legacy alias)
│   └── sanitize.py      # ensure_valid_username, sanitize_nick, xmpp_jid_or_plain_to_muc_nick, puppet_muc_nick_from_base
├── tracking/            # Cross-protocol message correlation
│   ├── base.py          # BidirectionalTTLMap (generic bidirectional TTL cache)
│   └── message_ids.py   # MessageIDResolver (per-protocol-pair ID mapping)
├── gateway/
│   ├── bus.py           # Event dispatcher
│   ├── relay.py         # MessageIn -> MessageOut routing
│   ├── router.py        # Channel mapping
│   ├── pipeline.py      # Pipeline, TransformContext, TransformStep protocol
│   ├── steps.py         # Default pipeline steps (spoiler, reply, filter, format)
│   └── msgid_resolver.py # MessageIDResolver port, DefaultMessageIDResolver
├── formatting/
│   ├── primitives.py    # FormattedText IR, Span, Style, CodeBlock, URL_RE, irc_casefold
│   ├── converter.py     # Registry-based convert(content, origin, target), strip_formatting
│   ├── markdown.py      # Discord markdown parser/emitter
│   ├── irc_codes.py     # IRC control code parser/emitter
│   ├── xmpp_styling.py  # XEP-0393 parser/emitter, XEP-0394 emitter
│   ├── splitter.py      # split_irc_message (byte-safe UTF-8 splitting)
│   ├── paste.py         # PrivateBin paste service integration
│   ├── mention_resolution.py  # @nick -> Discord <@userId> resolution
│   ├── reply_fallback.py      # Reply threading fallback
│   └── discord_to_xmpp.py     # Discord markdown -> XEP-0393 body + XEP-0394 spans
└── adapters/
    ├── base.py          # AdapterBase ABC
    ├── discord/         # DiscordAdapter: adapter, handlers, webhook, avatar, media, outbound
    ├── irc/             # IRCAdapter: adapter, client, handlers, outbound, puppet, msgid, throttle
    └── xmpp/            # XMPPAdapter: adapter, component, handlers, outbound, media, avatar, msgid
tests/                   # pytest suite (1505 tests)
├── unit/                # Isolated component tests (discord/, irc/, xmpp/, formatting/, gateway/, identity/, tracking/, config/, misc/)
├── property/            # Hypothesis property-based tests (24 correctness properties)
├── integration/         # Cross-component integration tests
└── offensive/           # Adversarial tests (injection, overflow, race conditions, Unicode edge cases)
```

## Common Tasks

### Development

- `uv sync` -- install all dependencies
- `uv run bridge --config config.yaml` -- run the bridge

### Quality

- `just bridge lint` -- ruff check (from root)
- `just bridge format` -- ruff format
- `just bridge typecheck` -- basedpyright
- `just bridge test` -- pytest (1514 tests)
- `just bridge test -k foo` -- run matching tests
- `just bridge check` -- all of the above in sequence

## Event System

All events are dataclasses in `events.py`. Factory functions (decorated with `@event`) return `(type_name, instance)` tuples.

| Event | Direction |
|-------|-----------|
| `MessageIn` / `MessageOut` | Inbound / outbound message |
| `MessageDelete` / `MessageDeleteOut` | Inbound / outbound delete (REDACT / retraction) |
| `ReactionIn` / `ReactionOut` | Inbound / outbound reaction |
| `TypingIn` / `TypingOut` | Inbound / outbound typing indicator |
| `Join` / `Part` / `Quit` | Presence events |
| `ConfigReload` | Dispatched on SIGHUP after config is reloaded |

## Configuration

Config is YAML + env overlay (dotenv loaded at startup). Generated by `scripts/prepare-config.sh` from `config.template.yaml` (run via `just init`). Key properties on `Config`:

| Property | Default | Description |
|----------|---------|-------------|
| `announce_joins_and_quits` | `true` | Relay join/part/quit to other protocols |
| `announce_extras` | `false` | Relay topic/mode changes |
| `content_filter_regex` | `[]` | Messages matching any pattern are not bridged |
| `identity_cache_ttl_seconds` | 3600 | TTL for Portal identity cache |
| `avatar_cache_ttl_seconds` | 86400 | TTL for avatar URL cache |
| `irc_puppet_idle_timeout_hours` | 24 | Disconnect idle puppets after N hours |
| `irc_puppet_ping_interval` | 120 | Keep-alive PING interval (seconds) |
| `irc_puppet_prejoin_commands` | `[]` | Commands sent after puppet connects (supports `{nick}`) |
| `irc_puppet_postfix` | `""` | Suffix appended to puppet nicks |
| `irc_throttle_limit` | 10 | IRC messages per second (token bucket) |
| `irc_message_queue` | 30 | Max IRC outbound queue size |
| `irc_rejoin_delay` | 5 | Seconds before rejoin after KICK/disconnect |
| `irc_auto_rejoin` | `true` | Auto-rejoin channels after KICK/disconnect |
| `irc_use_sasl` | `false` | Use SASL PLAIN for IRC auth |
| `irc_sasl_user` | `""` | SASL username |
| `irc_sasl_password` | `""` | SASL password |

## XMPP MUC puppet nick

Outbound MUC messages use a **per-Discord-user puppet** joined with `join_muc_wait` (`adapters/xmpp/component.py`). The occupant nick is resolved in `XMPPAdapter._resolve_nick_async` (`adapters/xmpp/adapter.py`):

1. **Portal / mapping:** `IdentityResolver.discord_to_xmpp` returns a **bare JID** (e.g. `alice@chat.example`). The bridge does **not** use the full string as the nick: it takes the **local part** only, then applies `sanitize_nick` (Prosody `muc_max_nick_length`, forbidden IRC/MUC characters). See `identity/sanitize.py` — `xmpp_jid_or_plain_to_muc_nick`.
2. **Dev / no XMPP mapping:** `discord_to_xmpp` is `None`; fallback is Discord **display name** (or author id slice), same sanitize path.
3. **Collision with a human:** XEP-0045 allows only one occupant per nick. If a real user is already in the room with the same nick, `join_muc_wait` can time out. Set env **`BRIDGE_XMPP_PUPPET_NICK_SUFFIX`** (e.g. `_d`) so the puppet nick differs; `puppet_muc_nick_from_base` appends it after sanitization. Documented in `.env.example` next to other bridge vars.

Echo suppression and stanza routing key off the same **nick string** passed to send and join; using the JID local part keeps server escaping consistent with `_recent_sent_nicks`.

## Critical Rules

- Never import one adapter from another -- all cross-adapter communication goes through the Bus.
- `uvloop.run()` is used on Linux/macOS; falls back to `asyncio.run()` on Windows.
- `AllowedMentions(everyone=False, roles=False)` on all webhook sends -- never allow mass pings from bridged content.
- Raw Discord events (`on_raw_*`) are used throughout -- never the cached variants.

## Finish the Task

- [ ] Run `just bridge check` before committing.
- [ ] Update the relevant `AGENTS.md` if you changed structure, entry points, or conventions.
- [ ] Update `README.md` if you changed setup steps, features, or test count.
- [ ] Summarize changes in conventional commit form (`feat:`, `fix:`, `docs:`, etc.).

## Related

- [docs/xmpp-muc-nick-findings.md](docs/xmpp-muc-nick-findings.md) — reference review notes (misc bridges, plans, specs)
- [Monorepo AGENTS.md](../../AGENTS.md)
- [src/AGENTS.md](src/AGENTS.md)
- [src/bridge/AGENTS.md](src/bridge/AGENTS.md)
- [src/bridge/adapters/AGENTS.md](src/bridge/adapters/AGENTS.md)
- [src/bridge/gateway/AGENTS.md](src/bridge/gateway/AGENTS.md)
- [src/bridge/formatting/AGENTS.md](src/bridge/formatting/AGENTS.md)
- [tests/AGENTS.md](tests/AGENTS.md)
