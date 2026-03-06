# atl.chat

> Scope: Monorepo root (applies to orchestration, shared tooling, and cross-app concerns).

Unified chat infrastructure for All Things Linux: IRC, XMPP, web, and protocol bridges.

## Quick Facts

- **Layout:** Monorepo with `apps/*` (UnrealIRCd, Atheme, Prosody, WebPanel, Web, Docs, Bridge, The Lounge, ObsidianIRC, Gamja)
- **Orchestration:** Docker Compose (root `compose.yaml` includes `infra/compose/*.yaml`)
- **Task Runner:** just (root + per-app via `mod`)
- **Key Commands:** `just init`, `just dev`, `just prod`, `just test`, `just test-all`

## Repository Structure

```
apps/
├── unrealircd/     # UnrealIRCd 6.x IRC server (config, Lua, scripts)
├── atheme/         # IRC services (NickServ, ChanServ, OperServ, MemoServ)
├── webpanel/       # UnrealIRCd web admin (nginx)
├── prosody/        # XMPP server (Lua config)
├── web/            # Next.js web application
├── bridge/         # Discord↔IRC↔XMPP bridge (Python, in-repo)
├── thelounge/      # Web IRC client (private mode, WebIRC, janitor/giphy plugins)
├── obsidianirc/    # Modern IRC web client (custom build)
├── gamja/          # IRC web client (planned)
├── docs/           # Fumadocs documentation site (Next.js)
└── fluux-messenger/ # Fluux XMPP messenger (nginx, Docker)

infra/
├── compose/        # Compose fragments: irc, xmpp, bridge, thelounge, obsidianirc, cert-manager, networks
├── nginx/          # Nginx config for Prosody HTTPS
└── turn-standalone/

scripts/            # init.sh, prepare-config.sh, gencloak-update-env.sh
tests/              # Root pytest suite (IRC, integration, e2e, protocol)
docs/               # Static assets (examples/unrealircd/tls/)
```

## Key Commands (Root)

| Command | Purpose |
|---------|---------|
| `just init` | Create data/ dirs, generate config, dev certs |
| `just dev` | Start stack with dev profile (.env.dev overlay) |
| `just prod` | Start production stack |
| `just down` | Stop dev stack |
| `just down-prod` | Stop production stack |
| `just logs [service]` | Follow logs |
| `just status` | Container status |
| `just test` | Run root pytest (tests/) |
| `just test-all` | Root tests + `just bridge test` |
| `just lint` | pre-commit run --all-files |
| `just scan` | Security scans (Gitleaks, Trivy) — placeholder |
| `just build` | docker compose build |
| `just clean` | Prune unused Docker resources and volumes |
| `just prosody-token` | Generate a non-expiring Prosody admin API Bearer token |

## Environment

- `.env` — Copy from `.env.example`; customize domains, passwords, tokens. Required for `just init` and compose.
- `.env.dev` — Overlay for `just dev`; override `IRC_DOMAIN`, `PROSODY_DOMAIN`, etc. for localhost. Required for `just dev`; copy from `.env.dev.example`.

## Per-App Commands (via `just <mod>`)

| Mod | Loads | Example |
|-----|-------|---------|
| `just irc` | apps/unrealircd | `just irc shell`, `just irc reload`, `just irc test`, `just irc sra-bootstrap <nick>` |
| `just xmpp` | apps/prosody | `just xmpp shell`, `just xmpp reload`, `just xmpp adduser`, `just xmpp check` |
| `just web` | apps/web | `just web dev`, `just web build`, `just web lint` |
| `just bridge` | apps/bridge | `just bridge test`, `just bridge check`, `just bridge lint` |
| `just lounge` | apps/thelounge | `just lounge add <name>`, `just lounge list`, `just lounge reset <name>` |
| `just obsidianirc` | apps/obsidianirc | `just obsidianirc shell`, `just obsidianirc rebuild`, `just obsidianirc rebuild-clean` |

## Related

- [apps/atheme/AGENTS.md](apps/atheme/AGENTS.md)
- [apps/bridge/AGENTS.md](apps/bridge/AGENTS.md)
- [apps/gamja/AGENTS.md](apps/gamja/AGENTS.md)
- [apps/obsidianirc/AGENTS.md](apps/obsidianirc/AGENTS.md)
- [apps/prosody/AGENTS.md](apps/prosody/AGENTS.md)
- [apps/thelounge/AGENTS.md](apps/thelounge/AGENTS.md)
- [apps/unrealircd/AGENTS.md](apps/unrealircd/AGENTS.md)
- [apps/web/AGENTS.md](apps/web/AGENTS.md)
- [apps/webpanel/AGENTS.md](apps/webpanel/AGENTS.md)
- [apps/docs/AGENTS.md](apps/docs/AGENTS.md)
- [apps/fluux-messenger/](apps/fluux-messenger/)
- [infra/AGENTS.md](infra/AGENTS.md)
- [scripts/AGENTS.md](scripts/AGENTS.md)
- [tests/AGENTS.md](tests/AGENTS.md)
- [README.md](README.md)

## Cursor Cloud specific instructions

### System dependencies (pre-installed by VM snapshot)

Docker, `just`, `uv`, `pnpm`, Node.js 22, Python 3.11+3.12, `envsubst` (gettext-base).
Docker daemon must be started manually: `sudo dockerd &>/tmp/dockerd.log &`. For non-root Docker access add your user to the `docker` group (`sudo usermod -aG docker $USER` then re-login), or prefix Docker commands with `sudo`. Avoid `chmod 666 /var/run/docker.sock` — it grants root-equivalent access to all local users.

### Starting the dev environment

1. **Env files**: `cp .env.example .env && cp .env.dev.example .env.dev` (idempotent; skip if files exist).
2. **Init + Docker stack**: `just dev` — runs `scripts/init.sh` (creates `data/` dirs, generates self-signed certs, substitutes config templates) then starts all Docker Compose services with the dev profile.
3. **Next.js web app**: `cd apps/web && NEXT_PUBLIC_IRC_WS_URL="ws://localhost:8000" NEXT_PUBLIC_XMPP_BOSH_URL="http://localhost:5280/http-bind" pnpm dev` (port 3000). This runs outside Docker as a local Node process.

### Service ports (dev profile)

| Service | Port | Notes |
|---------|------|-------|
| IRC (TLS) | 6697 | UnrealIRCd; self-signed cert for `irc.localhost` |
| IRC WebSocket | 8000 | UnrealIRCd WS |
| IRC RPC | 8600 | UnrealIRCd JSON-RPC |
| Atheme HTTP | 8081 | IRC services JSON-RPC |
| WebPanel | 8080 | UnrealIRCd admin panel |
| XMPP C2S | 5222 | Prosody client-to-server |
| XMPP HTTP | 5280 | Prosody BOSH/WebSocket |
| XMPP HTTPS | 5281 | Prosody (via nginx) |
| The Lounge | 9000 | Web IRC client (private mode; needs user created via `just lounge add`) |
| Dozzle | 8082 | Docker log viewer (dev profile only) |
| Next.js | 3000 | Web app (runs locally, not Docker) |

### Running tests

- **Unit tests** (fast, no Docker needed): `uv run pytest tests/unit/`
- **Bridge tests** (fast, no Docker needed): `uv run pytest apps/bridge/tests/`
- **Full root suite** (`just test`): includes integration tests that build Docker images — these may time out in constrained environments. Prefer running `tests/unit/` and `apps/bridge/tests/` for quick validation.
- **All tests**: `just test-all` (root tests + bridge tests).

### Running lint

`uv run pre-commit run --all-files` (equivalent to `just lint`). Requires Python 3.11 on PATH (installed by snapshot as `/usr/local/bin/python3.11`). Pre-existing lint warnings: luacheck warning in `apps/prosody/config/prosody.cfg.lua`.

### Gotchas

- **`CLOUDFLARE_DNS_API_TOKEN` warning**: Docker Compose emits a warning about this unset variable — safe to ignore in dev (cert-manager is not needed locally).
- **`pnpm install` build scripts warning**: esbuild/sharp/workerd build scripts are blocked by default. They have fallback binaries and the warning is non-blocking.
- **`apps/web` lint (`ultracite check`)**: Currently fails due to biome config expecting a `.gitignore` in `apps/web/`. This is a pre-existing issue. `pnpm run build` (Next.js build) works fine.
- **`pre-commit install`**: If `core.hooksPath` is set by the environment, run `git config --unset-all core.hooksPath` first.
- **Integration tests**: `tests/integration/` and `tests/e2e/` tests attempt to build fresh Docker images and may time out. Use `tests/unit/` for quick validation.
