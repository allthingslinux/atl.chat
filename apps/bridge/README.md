# ATL Bridge

**Production-ready Discord–IRC–XMPP bridge with multi-presence and Portal identity.**

[![Tests](https://img.shields.io/badge/tests-819%20passing-brightgreen)]() [![Python](https://img.shields.io/badge/python-3.10+-blue)]() [![License](https://img.shields.io/badge/license-MIT-blue)]()

## Overview

- **Multi-presence**: Each Discord user gets their own IRC connection and XMPP JID (puppets)
- **Identity-first**: Portal API is the source of truth—no account provisioning on the bridge
- **Event-driven**: All adapters communicate via a central Bus; no direct adapter-to-adapter calls
- **Modern protocols**: IRCv3 capabilities, XMPP XEPs for edits, reactions, replies, file transfers

## Quick Start

```bash
# From monorepo root
cd apps/bridge
uv sync

# Configure
cp config.example.yaml config.yaml
# Edit config.yaml with channel mappings

# Required env vars
export BRIDGE_DISCORD_TOKEN="your-token"
export BRIDGE_PORTAL_BASE_URL="https://portal.example.com"
export BRIDGE_PORTAL_TOKEN="your-portal-token"
export BRIDGE_XMPP_COMPONENT_JID="bridge.atl.chat"
export BRIDGE_XMPP_COMPONENT_SECRET="your-secret"

# Run
uv run bridge --config config.yaml
```

From monorepo root with `just`: `just bridge test`, `just bridge check`, etc. (see root [AGENTS.md](../../AGENTS.md)).

## Features

### Core

- **Channel mappings**: Config-based Discord channel ID ↔ IRC server/channel ↔ XMPP MUC JID
- **Message relay**: Bidirectional with edits, deletes, reactions, typing indicators
- **Content filtering**: Regex list; matching messages are not bridged
- **Identity resolution**: Portal API with configurable TTL cache
- **Message ID tracking**: IRC/XMPP msgid correlation for edit/delete (1h TTL)

### Discord

- **Webhooks**: Per-identity webhooks for native nick/avatar display
- **Raw events**: Edits and deletes fire for all messages (no cache dependency)
- **Bulk delete**: Moderator purges relay each deleted message
- **Mention safety**: `@everyone` and role pings suppressed
- **Mention resolution**: `@nick` in IRC/XMPP content resolved to `<@userId>` via guild member lookup
- **Media embedding**: Fetch image/video URLs from IRC/XMPP, send as Discord File
- **IRC formatting**: Bold, italic, underline, strikethrough (`\x1e` → `~~`) mapped to Discord markdown

### IRC

- **IRCv3**: message-tags, msgid, draft/reply, echo-message, labeled-response
- **Reply threading**: Discord replies ↔ IRC `+draft/reply` tags
- **Puppets**: Per-user connections with idle timeout (24h default), keep-alive PING, pre-join commands
- **Flood control**: Token bucket rate limiting, configurable throttle and queue size
- **SASL**: Optional PLAIN auth
- **RELAYMSG / REDACT**: UnrealIRCd relaymsg clean nicks; redact support (configurable)

### XMPP

- **Component protocol**: Single connection, multiple JIDs (XEP-0114)
- **Stream Management**: Reliable delivery with resumption (XEP-0198)
- **Corrections** (XEP-0308), **Retractions** (XEP-0424), **Reactions** (XEP-0444), **Replies** (XEP-0461), **Spoilers** (XEP-0382)
- **File transfers**: HTTP Upload (XEP-0363) with IBB fallback
- **OOB**: XEP-0066 Out of Band Data—extract file URLs from messages
- **JID escaping**: XEP-0106 for special characters in usernames

## Configuration

### Mappings

```yaml
mappings:
  - discord_channel_id: "123456789012345678"
    irc:
      server: irc.atl.chat
      port: 6697
      tls: true
      channel: "#bridge"
    xmpp:
      muc_jid: bridge@muc.atl.chat
```

### Key Options

| Option | Default | Description |
|--------|---------|-------------|
| `announce_joins_and_quits` | `true` | Relay join/part/quit to other protocols |
| `announce_extras` | `false` | Relay topic/mode changes |
| `content_filter_regex` | `[]` | Messages matching any pattern are not bridged |
| `identity_cache_ttl_seconds` | 3600 | Portal identity cache TTL |
| `avatar_cache_ttl_seconds` | 86400 | Avatar URL cache TTL |
| `irc_puppet_idle_timeout_hours` | 24 | Disconnect idle puppets after N hours |
| `irc_puppet_ping_interval` | 120 | Keep-alive PING interval (seconds) |
| `irc_puppet_prejoin_commands` | `[]` | Commands after connect (supports `{nick}`) |
| `irc_puppet_postfix` | `""` | Suffix for puppet nicks (e.g. `\|d`) |
| `irc_throttle_limit` | 10 | IRC messages per second |
| `irc_message_queue` | 30 | Max IRC outbound queue size |
| `irc_rejoin_delay` | 5 | Seconds before rejoin after KICK/disconnect |
| `irc_auto_rejoin` | `true` | Auto-rejoin after KICK/disconnect |
| `irc_use_sasl` | `false` | SASL PLAIN auth |
| `irc_tls_verify` | `true` | Verify IRC TLS (false for dev self-signed) |

See `config.example.yaml` for the full schema.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BRIDGE_DISCORD_TOKEN` | Yes | Discord bot token |
| `BRIDGE_PORTAL_BASE_URL` | Yes | Portal API URL |
| `BRIDGE_PORTAL_TOKEN` | Yes | Portal service token |
| `BRIDGE_XMPP_COMPONENT_JID` | Yes | Component JID (e.g. `bridge.atl.chat`) |
| `BRIDGE_XMPP_COMPONENT_SECRET` | Yes | Prosody component secret |
| `BRIDGE_XMPP_COMPONENT_SERVER` | No | Component host (default: `localhost`) |
| `BRIDGE_XMPP_COMPONENT_PORT` | No | Component port (default: `5347`) |
| `BRIDGE_IRC_NICK` | No | Main IRC nick (default: `bridge`) |

## Architecture

```
Discord Adapter  ──┐
IRC Adapter      ──→  Bus → Relay → Router → target adapters
XMPP Adapter     ──┘
```

- **Bus** (`gateway/bus.py`): Dispatches typed events to registered adapters
- **Relay** (`gateway/relay.py`): Transforms `MessageIn` → `MessageOut`; applies content filtering
- **Router** (`gateway/router.py`): Maps Discord channel IDs ↔ IRC channels ↔ XMPP MUCs
- **Identity** (`identity/`): Portal API client with TTL cache; resolves Discord ID → IRC nick / XMPP JID

### Project Structure

```
src/bridge/
├── __main__.py          # Entry point, signal handling
├── events.py            # Re-export from core.events
├── errors.py            # Re-export from core.errors
├── config/              # YAML + env overlay
│   ├── loader.py
│   └── schema.py
├── core/                # Domain primitives
│   ├── constants.py
│   ├── events.py
│   └── errors.py
├── identity/
│   ├── portal.py       # PortalClient, IdentityResolver
│   └── dev.py          # DevIdentityResolver
├── gateway/
│   ├── bus.py
│   ├── relay.py
│   ├── router.py
│   └── msgid_resolver.py
├── formatting/
│   ├── discord_to_irc.py
│   ├── irc_to_discord.py
│   ├── irc_message_split.py
│   ├── reply_fallback.py
│   └── mention_resolution.py
└── adapters/
    ├── base.py
    ├── discord/         # adapter, handlers, webhook
    ├── irc/              # adapter, client, puppet, msgid, throttle
    └── xmpp/             # adapter, component, msgid
```

## Development

```bash
uv sync
uv run pytest tests -v
uv run ruff check src tests
uv run basedpyright
```

Or from monorepo root: `just bridge test`, `just bridge check`, `just bridge lint`, `just bridge format`, `just bridge typecheck`.

## Docker

Build from **monorepo root** (context must include `pyproject.toml`, `uv.lock`, `apps/bridge/`):

```bash
docker build -f apps/bridge/Containerfile -t atl-bridge .
```

Run:

```bash
docker run -v /path/to/config.yaml:/app/config.yaml \
  -e BRIDGE_DISCORD_TOKEN="..." \
  -e BRIDGE_PORTAL_BASE_URL="..." \
  -e BRIDGE_PORTAL_TOKEN="..." \
  -e BRIDGE_XMPP_COMPONENT_JID="..." \
  -e BRIDGE_XMPP_COMPONENT_SECRET="..." \
  atl-bridge
```

## XMPP Setup

Prosody (or compatible server) must have a component configured for `BRIDGE_XMPP_COMPONENT_JID` with the component secret matching `BRIDGE_XMPP_COMPONENT_SECRET`.

## Limitations

- **Single guild**: One bridge instance per Discord guild
- **No DMs**: Only channels/MUCs, no private messages
- **File size**: 10MB limit for XMPP file transfers
- **IRC puppet timeout**: Idle puppets disconnect after 24h (configurable)

## License

MIT (see `pyproject.toml`).
