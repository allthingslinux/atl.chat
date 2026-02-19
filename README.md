# ATL Bridge

Custom Discord–IRC–XMPP bridge with multi-presence. Portal is the identity source; no account provisioning on the bridge.

## Features

- **Event bus** — Central dispatcher; adapters produce/consume typed events
- **Multi-presence** — Webhooks per IRC nick / XMPP JID for Discord; IRC puppets for Discord users (when linked in Portal)
- **Channel mappings** — Config maps Discord channel ↔ IRC server/channel ↔ XMPP MUC
- **Identity** — Portal API (or read-only DB) for Discord ID ↔ IRC nick ↔ XMPP JID
- **IRCv3 support** — Message IDs, reply threading, extended capabilities
- **XEP-0198** — Stream Management for reliable XMPP message delivery and resumption
- **XEP-0203** — Delayed Delivery to filter MUC history and prevent duplicate messages
- **XEP-0308** — Last Message Correction for Discord ↔ XMPP message editing
- **XEP-0363** — HTTP File Upload for efficient file transfers
- **XEP-0372** — References for reply threading and mentions
- **XEP-0382** — Spoiler Messages for content warnings
- **XEP-0422** — Message Fastening for attaching metadata to messages
- **XEP-0424** — Message Retraction for message deletion
- **XEP-0444** — Message Reactions for emoji reactions
- **XEP-0461** — Message Replies for reply threading

## IRCv3 Capabilities

The bridge supports modern IRCv3 features:

- **message-tags** — Parse and send IRCv3 message tags
- **msgid** — Track message IDs for edit/delete correlation
- **draft/reply** — Thread replies between Discord and IRC
- **account-notify** — Track account authentication status
- **extended-join** — Enhanced join information
- **server-time** — Accurate message timestamps
- **batch** — Handle grouped messages (netsplits, chat history)
- **echo-message** — Confirm message delivery and track puppet sends
- **labeled-response** — Correlate commands with responses across connections
- **chghost** — Track username/hostname changes without fake QUIT/JOIN
- **setname** — Track realname (GECOS) changes

### JID Escaping (XEP-0106)

The bridge uses XEP-0106 to escape special characters in usernames when creating XMPP JIDs:
- Discord/IRC usernames with `@`, `#`, `:`, `/`, etc. are properly escaped
- Example: `User#1234` → `user\231234@bridge.atl.chat`
- Prevents invalid JIDs and ensures compatibility with all username formats

### Message ID Tracking

IRC message IDs are tracked with a 1-hour TTL cache for:
- Correlating edits/deletes between platforms
- Maintaining reply threading context
- Debugging message flow

### Reply Threading

When a Discord user replies to a message:
1. Bridge looks up the IRC msgid from the original message
2. Sends the reply with `+draft/reply` tag pointing to the original
3. IRC clients supporting the capability show proper threading

When an IRC user replies:
1. Bridge extracts `+draft/reply` tag from incoming message
2. Resolves IRC msgid to Discord message ID
3. Creates Discord reply to the original message

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) or pip

## Setup

```bash
uv sync --all-extras   # or: pip install -e ".[dev]"
cp config.example.yaml config.yaml
# Edit config.yaml with your mappings
```

## Configuration

See `config.example.yaml`. Key sections:

- **mappings** — List of Discord channel ID ↔ IRC ↔ XMPP MUC
- **announce_joins_and_quits** — Relay join/part/quit (default: true)
- **irc_puppet_idle_timeout_hours** — Idle timeout for IRC puppets (default: 24)

### IRC Puppet Manager

The bridge creates separate IRC connections for each Discord user (when linked in Portal):
- Puppets use the user's IRC nick from Portal
- Idle puppets disconnect after 24 hours (configurable via `IRC_PUPPET_IDLE_TIMEOUT_HOURS` env var)
- Automatic cleanup runs hourly
- Falls back to main connection for unlinked users

### XMPP Component (Multi-Presence)

The bridge uses XMPP ComponentXMPP for multi-presence (puppets):
- Each Discord user appears as a unique JID (e.g., `username@bridge.atl.chat`)
- Single component connection handles all user identities
- Requires Prosody component configuration (see `XMPP_COMPONENT_CONFIG.md`)

### XEP-0363: HTTP File Upload

The bridge uses HTTP File Upload with IBB fallback for file transfers:
- **Discord → XMPP**: Downloads Discord attachments, tries HTTP upload first, falls back to IBB if unavailable
- **XMPP → Discord**: Receives IBB streams and uploads to Discord channels
- **IRC integration**: Discord attachments sent as URLs to IRC; XMPP files trigger notification in IRC
- Max file size: 10MB
- HTTP upload preferred for efficiency; IBB used as fallback
- Requires XMPP server with HTTP upload service (or falls back to IBB)

## Environment variables (secrets)

| Variable | Description |
|----------|-------------|
| `DISCORD_TOKEN` | Discord bot token |
| `PORTAL_BASE_URL` | Portal API base URL (e.g. `https://portal.example.com`) |
| `PORTAL_TOKEN` | Portal API token (service auth) |
| `IRC_NICK` | IRC main connection nick (default: `atl-bridge`) |
| `XMPP_COMPONENT_JID` | XMPP component JID (e.g., `bridge.atl.chat`) |
| `XMPP_COMPONENT_SECRET` | Shared secret for component authentication |
| `XMPP_COMPONENT_SERVER` | Prosody server hostname (default: `localhost`) |
| `XMPP_COMPONENT_PORT` | Component port (default: `5347`) |

## Run

```bash
bridge --config config.yaml
# or: python -m bridge --config config.yaml
```

## Docker

```bash
# Build
uv run uv build   # or: docker build -f Containerfile -t atl-bridge .

# Run (bind-mount config)
docker run -v $(pwd)/config.yaml:/app/config.yaml \
  -e DISCORD_TOKEN=... \
  -e XMPP_JID=... -e XMPP_PASSWORD=... \
  atl-bridge
```

## Single-guild caveat

One bridge instance per Discord guild. Do not use the same bot across multiple guilds without clear documentation.

## Project structure

- `src/bridge/` — Core: config, events, identity, gateway
- `src/bridge/adapters/` — Discord, IRC, XMPP adapters
- `audit/` — Reference audits and consensus (AUDIT.md, STRUCTURE.md)

## Tests

```bash
uv run pytest tests -v
uv run ruff check src tests
```

## License

MIT
