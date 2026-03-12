# apps/obsidianirc

> Scope: ObsidianIRC web client (custom build from upstream submodule).

Modern IRC web client with ATL-specific configuration baked in.

## Quick Facts

- **Upstream:** [ObsidianIRC](https://github.com/irctoday/ObsidianIRC) (git submodule at `upstream/`)
- **Build:** Custom Containerfile with VITE build args
- **Config:** `VITE_HIDE_SERVER_LIST=true` hides multi-server UI; defaults to ATL IRC
- **Port:** 8090 (configurable via `OBSIDIANIRC_PORT`)

## Structure

```
apps/obsidianirc/
├── Containerfile       # Custom build with ATL defaults
├── justfile            # shell, logs, rebuild, rebuild-clean
└── upstream/           # Git submodule (ObsidianIRC source)
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `just obsidianirc shell` | Open shell in container |
| `just obsidianirc logs` | Follow container logs |
| `just obsidianirc rebuild` | Rebuild image |
| `just obsidianirc rebuild-clean` | Rebuild without cache |

## Environment Variables

Set in `.env` / `.env.dev`:

- `OBSIDIANIRC_PORT` — Host port (default: 8090)
- `OBSIDIANIRC_IRC_WS_URL` — WebSocket URL (default: `wss://irc.atl.chat/ws`)
- `OBSIDIANIRC_AUTOJOIN` — Comma-separated channels (default: `#general`)

## Build Args

Baked into the image at build time:

- `VITE_DEFAULT_IRC_SERVER` — WebSocket URL
- `VITE_DEFAULT_IRC_SERVER_NAME` — "ATL IRC"
- `VITE_DEFAULT_IRC_CHANNELS` — Auto-join channels
- `VITE_HIDE_SERVER_LIST` — "true" (hides Discover page)

## Compose

Defined in `infra/compose/obsidianirc.yaml`. Depends on `atl-irc-server` (UnrealIRCd).

## Dev: Self-signed cert (Firefox)

In dev, the WebSocket uses `wss://127.0.0.1:8000` with a self-signed cert. Firefox blocks WebSocket connections to untrusted certs without prompting. Add an exception first: visit `https://127.0.0.1:8000/` → Advanced → Accept the Risk and Continue. Then ObsidianIRC will connect.

## Related

- [infra/compose/obsidianirc.yaml](../../infra/compose/obsidianirc.yaml)
- [upstream/README.md](upstream/README.md) — ObsidianIRC upstream docs
- [Root AGENTS.md](../../AGENTS.md)
