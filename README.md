# ATL Bridge

**Production-ready Discord–IRC–XMPP bridge with multi-presence and modern protocol support.**

[![Tests](https://img.shields.io/badge/tests-654%20passing-brightgreen)]() [![Python](https://img.shields.io/badge/python-3.10+-blue)]() [![License](https://img.shields.io/badge/license-MIT-blue)]()

## Why ATL Bridge?

- **Multi-presence**: Each Discord user gets their own IRC connection and XMPP JID (puppets)
- **Modern protocols**: IRCv3 capabilities, XMPP XEPs for edits/reactions/replies
- **Identity-first**: Portal is the source of truth—no account provisioning on the bridge
- **Production-ready**: Comprehensive test suite, retry logic, error recovery

## Quick Start

```bash
# Install
uv sync

# Configure
cp config.example.yaml config.yaml
# Edit config.yaml with your channels and credentials

# Run
export DISCORD_TOKEN="your-token"
export PORTAL_BASE_URL="https://portal.example.com"
export PORTAL_TOKEN="your-portal-token"
export XMPP_COMPONENT_JID="bridge.atl.chat"
export XMPP_COMPONENT_SECRET="your-secret"

bridge --config config.yaml
```

## Features

### Core Bridging
- **Event-driven architecture**: Central event bus with typed events (MessageIn/Out, Join, Part, Delete, Reaction, Typing)
- **Channel mappings**: Config-based Discord ↔ IRC ↔ XMPP routing
- **Identity resolution**: Portal API integration with configurable TTL caching
- **Message relay**: Bidirectional with edit/delete support; content filtering (regex)

### IRC Support
- **IRCv3 capabilities**: message-tags, msgid, draft/reply, echo-message, labeled-response
- **Reply threading**: Discord replies ↔ IRC `+draft/reply` tags
- **Typing indicators**: Discord typing → IRC `TAGMSG` with `+typing=active`
- **Puppet management**: Per-user connections with idle timeout (24h default)
- **Puppet keep-alive**: Configurable PING interval to prevent silent server-side drops
- **Pre-join commands**: Send NickServ IDENTIFY, MODE, etc. immediately after puppet connects
- **Message ID tracking**: 1-hour TTL cache for edit/delete correlation
- **Flood control**: Token bucket rate limiting and configurable throttle

### XMPP Support
- **Component protocol**: Single connection, multiple JIDs (XEP-0114)
- **Stream Management**: Reliable delivery with resumption (XEP-0198)
- **Message features**:
  - Corrections (XEP-0308) - Edit messages
  - Retractions (XEP-0424) - Delete messages
  - Reactions (XEP-0444) - Emoji reactions
  - Replies (XEP-0461) - Reply threading
  - Spoilers (XEP-0382) - Content warnings
- **File transfers**: HTTP Upload (XEP-0363) with IBB fallback
- **JID escaping**: XEP-0106 for special characters in usernames
- **History filtering**: XEP-0203 delayed delivery detection

### Discord Support
- **Webhooks**: Per-identity webhooks for native nick/avatar display
- **Raw event handling**: Edits and deletes fire for all messages, not just cached ones
- **Bulk delete**: Moderator purges relay each deleted message to IRC/XMPP
- **Message edits**: XMPP corrections and IRC edits → Discord `edit_message`
- **Reactions**: Add and remove reactions bridged to/from IRC/XMPP
- **Typing indicators**: IRC typing → Discord `channel.typing()`
- **Mention safety**: `@everyone` and role pings suppressed on bridged content
- **!bridge status**: Show linked IRC/XMPP accounts (requires Portal identity)

### Reliability
- **Retry logic**: Exponential backoff for transient errors (5 attempts, 2-30s)
- **Error recovery**: Graceful handling of network failures
- **Event loop**: uvloop for 2-4x faster async I/O (Linux/macOS; falls back to asyncio on Windows)
- **Comprehensive tests**: 654 tests covering core, adapters, formatting, and edge cases

## Configuration

### Minimal Example

```yaml
mappings:
  - discord_channel_id: "123456789012345678"
    irc:
      server: "irc.libera.chat"
      port: 6697
      tls: true
      channel: "#atl"
    xmpp:
      muc_jid: "atl@conference.example.com"

announce_joins_and_quits: true
irc_puppet_idle_timeout_hours: 24
irc_puppet_ping_interval: 120        # keep-alive PING every 2 minutes
irc_puppet_prejoin_commands:         # sent immediately after puppet connects
  - "MODE {nick} +D"
```

See `config.example.yaml` for all options (throttling, SASL, content filtering, etc.).

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_TOKEN` | Yes | Discord bot token |
| `PORTAL_BASE_URL` | Yes | Portal API URL |
| `PORTAL_TOKEN` | Yes | Portal service token |
| `XMPP_COMPONENT_JID` | Yes | Component JID (e.g., `bridge.atl.chat`) |
| `XMPP_COMPONENT_SECRET` | Yes | Prosody component secret |
| `XMPP_COMPONENT_SERVER` | No | Server hostname (default: `localhost`) |
| `XMPP_COMPONENT_PORT` | No | Component port (default: `5347`) |
| `IRC_NICK` | No | Main IRC nick (default: `atl-bridge`) |

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │         Discord Bot                 │
                    │   Webhooks + Message Events         │
                    └──────────────┬──────────────────────┘
                                   │
                                   │ MessageIn/MessageOut
                                   │ Join/Part/Quit
                                   ▼
                    ┌─────────────────────────────────────┐
                    │         Event Bus                   │
                    │   Async dispatch + Error isolation  │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
         ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
         │   Channel    │  │   Identity   │  │  Message ID  │
         │   Router     │  │   Resolver   │  │   Trackers   │
         │              │  │              │  │              │
         │  Discord ↔   │  │ Portal API + │  │ IRC + XMPP   │
         │  IRC ↔ XMPP  │  │  TTL cache   │  │   1hr TTL    │
         └──────────────┘  └──────────────┘  └──────────────┘
                    │              │              │
                    └──────────────┼──────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
         ┌─────────────────────┐      ┌─────────────────────┐
         │   IRC Adapter       │      │   XMPP Component    │
         │                     │      │                     │
         │ • Main connection   │      │ • ComponentXMPP     │
         │ • Puppet manager    │      │ • Multi-presence    │
         │ • IRCv3 caps        │      │ • 8 XEPs            │
         │ • 24h idle timeout  │      │ • Stream mgmt       │
         └─────────────────────┘      └─────────────────────┘
                    │                             │
                    ▼                             ▼
         ┌─────────────────────┐      ┌─────────────────────┐
         │  IRC Server         │      │  XMPP Server        │
         │  (unrealircd)       │      │  (prosody)          │
         └─────────────────────┘      └─────────────────────┘
```

### Data Flow

**Discord → IRC/XMPP:**
1. Discord user sends message
2. Discord adapter creates `MessageIn` event
3. Event bus dispatches to all adapters
4. Identity resolver checks Portal for IRC/XMPP links
5. Channel router finds target IRC channel + XMPP MUC
6. IRC adapter sends via puppet (if linked) or main connection
7. XMPP component sends from user's JID (e.g., `user@bridge.atl.chat`)

**IRC → Discord/XMPP:**
1. IRC puppet receives message with `msgid` tag
2. IRC adapter creates `MessageIn` event, stores msgid mapping
3. Event bus dispatches to Discord + XMPP adapters
4. Discord adapter sends via webhook (shows IRC nick)
5. XMPP component relays to MUC from bridge JID

**Edit/Delete Flow:**
1. Discord edit event received → Relay emits MessageOut with `is_edit`
2. IRC/XMPP adapters look up stored msgid; Discord adapter resolves via trackers
3. IRC: `TAGMSG` with edit; XMPP: correction (XEP-0308); Discord: `webhook.edit_message`
4. IRC REDACT / XMPP retraction → Discord `message.delete`

**Reactions & Typing:**
- Discord reactions → Relay → IRC/XMPP; IRC/XMPP reactions → Relay → Discord
- Typing indicators bridged both directions (Discord ↔ IRC; throttled)

### Key Components

- **Event Bus**: Central dispatcher for typed events (MessageIn, MessageOut, Join, Part, Quit, MessageDelete, ReactionIn/Out, TypingIn/Out)
- **Relay**: Transforms MessageIn → MessageOut for target protocols; applies content filtering and formatting
- **Channel Router**: Maps Discord channels ↔ IRC channels ↔ XMPP MUCs
- **Identity Resolver**: Portal API client with configurable TTL caching
- **Adapters**: Protocol-specific handlers (Discord, IRC, XMPP)

## Development

### Setup

```bash
# Install with dev dependencies
uv sync

# Run tests
uv run pytest tests -v

# Linting
uv run ruff check src tests
uv run basedpyright
```

### Project Structure

```
src/bridge/
├── __main__.py          # Entry point
├── config.py            # YAML config loading
├── events.py            # Event types
├── identity.py          # Portal client + cache
├── gateway/
│   ├── bus.py          # Event dispatcher
│   ├── relay.py        # MessageIn → MessageOut routing
│   └── router.py       # Channel mapping
├── formatting/
│   ├── discord_to_irc.py   # Discord markdown → IRC
│   ├── irc_to_discord.py   # IRC control codes → Discord
│   └── irc_message_split.py  # Long message splitting
└── adapters/
    ├── base.py         # Adapter interface
    ├── disc.py         # Discord adapter
    ├── irc.py          # IRC client
    ├── irc_puppet.py   # IRC puppet manager
    ├── irc_throttle.py # IRC flood control
    ├── irc_msgid.py    # IRC message ID tracker
    ├── xmpp.py         # XMPP adapter
    ├── xmpp_component.py   # XMPP component
    └── xmpp_msgid.py   # XMPP message ID tracker
```

### Testing

```bash
# All tests
uv run pytest tests -v

# Specific feature
uv run pytest tests/test_xmpp_features.py -v

# With coverage
uv run pytest tests --cov --cov-report=html
```

**Test Coverage**: 654 tests covering:
- Core bridging logic and relay
- Discord adapter (webhooks, edits, reactions, typing)
- IRC reply threading, puppets, message ID tracking
- XMPP XEPs (8 extensions), message ID tracking
- Formatting (Discord↔IRC, message splitting)
- File transfers
- Error handling
- Concurrency and ordering

## Docker

```bash
# Build
docker build -f Containerfile -t atl-bridge .

# Run
docker run -v $(pwd)/config.yaml:/app/config.yaml \
  -e DISCORD_TOKEN="..." \
  -e PORTAL_BASE_URL="..." \
  -e PORTAL_TOKEN="..." \
  -e XMPP_COMPONENT_JID="..." \
  -e XMPP_COMPONENT_SECRET="..." \
  atl-bridge
```

## XMPP Server Setup

The bridge requires Prosody (or compatible XMPP server) with component configuration. Configure a component for the `XMPP_COMPONENT_JID` and set the component secret to match `XMPP_COMPONENT_SECRET`.

## Limitations

- **Single guild**: One bridge instance per Discord guild
- **No DMs**: Only channels/MUCs, no private messages
- **File size**: 10MB limit for XMPP file transfers
- **IRC puppet timeout**: Idle puppets disconnect after 24 hours (configurable)

## Troubleshooting

### Bridge not connecting to IRC
- Check firewall rules for IRC ports (6667, 6697)
- Verify IRC server allows multiple connections from same IP
- Check IRC nick is not already in use

### XMPP messages not bridging
- Verify Prosody component configuration
- Check component secret matches
- Ensure MUC exists and bridge has joined
- Review Prosody logs: `/var/log/prosody/prosody.log`

### Discord messages delayed
- Check Portal API is responding (< 100ms)
- Verify identity cache is working (check logs)
- Monitor event bus queue depth

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass: `uv run pytest tests -v`
5. Run linters: `uv run ruff check src tests`
6. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built for [All Things Linux](https://discord.gg/linux)
- Uses [discord.py](https://github.com/Rapptz/discord.py) for Discord
- Uses [pydle](https://github.com/Shizmob/pydle) for IRC
- Uses [slixmpp](https://github.com/poezio/slixmpp) for XMPP

---

**Status**: Production-ready • **Maintained**: Yes • **Tests**: 654 passing
