# ObsidianIRC

Modern IRC web client for All Things Linux, built from the [ObsidianIRC](https://github.com/irctoday/ObsidianIRC) upstream with ATL-specific defaults.

## Features

- Modern, responsive UI
- WebSocket-based IRC connection
- Auto-join configured channels
- Single-server mode (multi-server UI hidden)
- Pre-configured for ATL IRC

## Configuration

The client is built with ATL defaults baked in via Vite build args:

- **Server:** `wss://irc.atl.chat/ws` (or `OBSIDIANIRC_IRC_WS_URL` from `.env`)
- **Auto-join:** `#general` (or `OBSIDIANIRC_AUTOJOIN` from `.env`)
- **Server list:** Hidden (single-server mode)

## Usage

### Development

```bash
# Start the stack (includes ObsidianIRC)
just dev

# Access at http://localhost:8090
```

### Production

```bash
# Start the stack
just prod

# Access at http://<your-domain>:8090
```

### Rebuilding

If you modify the Containerfile or want to pull upstream changes:

```bash
# Rebuild the image
just obsidianirc rebuild

# Rebuild without cache (clean build)
just obsidianirc rebuild-clean
```

## Environment Variables

Set in `.env` or `.env.dev`:

```bash
OBSIDIANIRC_PORT=8090                           # Host port
OBSIDIANIRC_IRC_WS_URL=wss://irc.atl.chat/ws   # WebSocket URL
OBSIDIANIRC_AUTOJOIN=#general                   # Auto-join channels
```

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
