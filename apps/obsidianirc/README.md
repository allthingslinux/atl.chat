# ObsidianIRC

Modern IRC web client for All Things Linux, built from the [ObsidianIRC](https://github.com/irctoday/ObsidianIRC) upstream with ATL-specific defaults.

## Features

- Modern, responsive UI
- WebSocket-based IRC connection
- Auto-join configured channels
- Single-server mode (multi-server UI hidden)
- Pre-configured for ATL IRC

## Local Development

`just dev` loads `.env` then `.env.dev`; build args are baked in at image build time.

**Prerequisites:** Copy `.env.dev.example` to `.env.dev` if you haven't already.

```bash
# Start the stack (loads .env + .env.dev)
just dev

# Access at http://localhost:8090
```

**Dev defaults** (from `.env.dev`):

| Variable | Dev value | Purpose |
|----------|-----------|---------|
| `OBSIDIANIRC_PORT` | `8090` | Host port for the web UI |
| `OBSIDIANIRC_IRC_WS_URL` | `ws://127.0.0.1:8000` | Direct WebSocket to UnrealIRCd (no TLS; use 127.0.0.1 to avoid IPv6 localhost) |
| `OBSIDIANIRC_AUTOJOIN` | `#general` | Channels to auto-join |
| `OBSIDIANIRC_SERVER_NAME` | `irc.localhost` | Display name in the UI |

The browser connects to `ws://127.0.0.1:8000` (IRC WebSocket) and `http://localhost:8090` (ObsidianIRC). Use `127.0.0.1` for the WebSocket to avoid IPv6 `localhost` resolution issues.

## Production

`just prod` loads `.env` only. WebSocket URL goes through NPM (TLS termination).

```bash
# Start the stack
just prod

# Access at https://irc.atl.chat (or your configured domain)
```

**Prod defaults** (from `.env`):

| Variable | Prod value | Purpose |
|----------|------------|---------|
| `OBSIDIANIRC_PORT` | `8090` | Host port (or omit if behind reverse proxy) |
| `OBSIDIANIRC_IRC_WS_URL` | `wss://irc.atl.chat/ws` | WebSocket via NPM (TLS) |
| `OBSIDIANIRC_AUTOJOIN` | `#general` | Channels to auto-join |
| `OBSIDIANIRC_SERVER_NAME` | `ATL IRC` | Display name in the UI |

## Rebuilding

Build args are baked in at build time. Rebuild when you change `.env` / `.env.dev` or the Containerfile:

```bash
# Rebuild and restart
just obsidianirc rebuild

# Rebuild without cache (use when switching dev ↔ prod or after upstream changes)
just obsidianirc rebuild-clean
```

## Environment Variables

Set in `.env` (production) or `.env.dev` (development overlay):

| Variable | Default | Description |
|----------|---------|-------------|
| `OBSIDIANIRC_PORT` | `8090` | Host port for the web UI |
| `OBSIDIANIRC_IRC_WS_URL` | `wss://irc.atl.chat/ws` | WebSocket URL (baked into build) |
| `OBSIDIANIRC_SERVER_NAME` | `ATL IRC` | Server name shown in the UI |
| `OBSIDIANIRC_AUTOJOIN` | `#general` | Comma-separated channels to auto-join |

## Upstream

The `upstream/` directory is a git submodule pointing to the official ObsidianIRC repository. See [upstream/README.md](upstream/README.md) for upstream documentation.

To update the submodule:

```bash
cd apps/obsidianirc/upstream
git pull origin main
cd ../../..
git add apps/obsidianirc/upstream
git commit -m "chore(obsidianirc): update upstream submodule"
```

## Architecture

- **Build:** Custom Containerfile that builds the Vite app with ATL defaults
- **Runtime:** Nginx serving static files
- **Dependencies:** Requires UnrealIRCd (`atl-irc-server`) to be running

## Related

- [Containerfile](Containerfile) — Custom build configuration
- [justfile](justfile) — Build commands
- [infra/compose/obsidianirc.yaml](../../infra/compose/obsidianirc.yaml) — Compose service definition
- [upstream/README.md](upstream/README.md) — ObsidianIRC upstream docs
