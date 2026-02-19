# ATL Bridge

**Production-ready Discord–IRC–XMPP bridge with multi-presence and modern protocol support.**

[![Tests](https://img.shields.io/badge/tests-215%20passing-brightgreen)]() [![Python](https://img.shields.io/badge/python-3.10+-blue)]() [![License](https://img.shields.io/badge/license-MIT-blue)]()

## Why ATL Bridge?

- **Multi-presence**: Each Discord user gets their own IRC connection and XMPP JID (puppets)
- **Modern protocols**: IRCv3 capabilities, XMPP XEPs for edits/reactions/replies
- **Identity-first**: Portal is the source of truth—no account provisioning on the bridge
- **Production-ready**: Comprehensive test suite, retry logic, error recovery

## Quick Start

```bash
# Install
uv sync --all-extras

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
- **Event-driven architecture**: Central event bus with typed events
- **Channel mappings**: Config-based Discord ↔ IRC ↔ XMPP routing
- **Identity resolution**: Portal API integration with TTL caching
- **Message relay**: Bidirectional with edit/delete support

### IRC Support
- **IRCv3 capabilities**: message-tags, msgid, draft/reply, echo-message, labeled-response
- **Reply threading**: Discord replies ↔ IRC `+draft/reply` tags
- **Puppet management**: Per-user connections with idle timeout (24h default)
- **Message ID tracking**: 1-hour TTL cache for edit/delete correlation

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

### Reliability
- **Retry logic**: Exponential backoff for transient errors (5 attempts, 2-30s)
- **Error recovery**: Graceful handling of network failures
- **Comprehensive tests**: 215 tests covering core and edge cases

## Configuration

### Minimal Example

```yaml
mappings:
  - discord_channel_id: "123456789"
    irc:
      server: "irc.libera.chat"
      channel: "#atl"
    xmpp:
      muc_jid: "atl@conference.example.com"

announce_joins_and_quits: true
irc_puppet_idle_timeout_hours: 24
```

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
┌─────────────┐
│   Discord   │
└──────┬──────┘
       │
       ├─────────┐
       │         │
┌──────▼──────┐  │
│  Event Bus  │◄─┤
└──────┬──────┘  │
       │         │
       ├─────────┤
       │         │
┌──────▼──────┐  │
│     IRC     │  │
│  (puppets)  │  │
└─────────────┘  │
       │         │
┌──────▼──────┐  │
│    XMPP     │◄─┘
│ (component) │
└─────────────┘
```

### Key Components

- **Event Bus**: Central dispatcher for typed events (MessageIn, MessageOut, Join, Part, Quit)
- **Channel Router**: Maps Discord channels ↔ IRC channels ↔ XMPP MUCs
- **Identity Resolver**: Portal API client with caching (5min TTL)
- **Adapters**: Protocol-specific handlers (Discord, IRC, XMPP)

## Development

### Setup

```bash
# Install with dev dependencies
uv sync --all-extras

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
│   └── router.py       # Channel mapping
└── adapters/
    ├── disc.py         # Discord adapter
    ├── irc.py          # IRC client
    ├── irc_puppet.py   # IRC puppet manager
    ├── irc_msgid.py    # IRC message ID tracker
    ├── xmpp_component.py  # XMPP component
    └── xmpp_msgid.py   # XMPP message ID tracker
```

### Testing

```bash
# All tests
uv run pytest tests -v

# Specific feature
uv run pytest tests/test_xmpp_features.py -v

# With coverage
uv run pytest tests --cov=src/bridge --cov-report=html
```

**Test Coverage**: 215 tests covering:
- Core bridging logic
- IRC reply threading
- XMPP XEPs (8 extensions)
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

The bridge requires Prosody with component configuration. See [`XMPP_COMPONENT_CONFIG.md`](XMPP_COMPONENT_CONFIG.md) for setup instructions.

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

**Status**: Production-ready • **Maintained**: Yes • **Tests**: 215 passing
