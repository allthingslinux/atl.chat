# ATL Bridge

Custom Discord–IRC–XMPP bridge with multi-presence. Portal is the identity source; no account provisioning on the bridge.

## Features

- **Event bus** — Central dispatcher; adapters produce/consume typed events
- **Multi-presence** — Webhooks per IRC nick / XMPP JID for Discord; IRC puppets for Discord users (when linked in Portal)
- **Channel mappings** — Config maps Discord channel ↔ IRC server/channel ↔ XMPP MUC
- **Identity** — Portal API (or read-only DB) for Discord ID ↔ IRC nick ↔ XMPP JID

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

## Environment variables (secrets)

| Variable | Description |
|----------|-------------|
| `DISCORD_TOKEN` | Discord bot token |
| `PORTAL_BASE_URL` | Portal API base URL (e.g. `https://portal.example.com`) |
| `PORTAL_TOKEN` | Portal API token (service auth) |
| `IRC_NICK` | IRC main connection nick (default: `atl-bridge`) |
| `XMPP_JID` | XMPP JID for MUC client |
| `XMPP_PASSWORD` | XMPP password |
| `XMPP_NICK` | MUC nickname (default: `atl-bridge`) |

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
