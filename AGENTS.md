# atl.chat

> Scope: Monorepo root (applies to orchestration, shared tooling, and cross-app concerns).

Unified chat infrastructure for All Things Linux: IRC, XMPP, web, and protocol bridges.

## Quick Facts

- **Layout:** Monorepo with `apps/*` (UnrealIRCd, Atheme, Prosody, WebPanel, Web, Bridge, Gamja)
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
└── gamja/          # IRC web client (planned)

infra/
├── compose/        # Compose fragments: irc, xmpp, bridge, cert-manager, networks
└── turn-standalone/

scripts/            # init.sh, prepare-config.sh, gencloak-update-env.sh
tests/              # Root pytest suite (IRC, integration, e2e, protocol)
docs/               # Architecture, services, onboarding, bridges
```

## Key Commands (Root)

| Command | Purpose |
|---------|---------|
| `just init` | Create data/ dirs, generate config, dev certs |
| `just dev` | Start stack with dev profile (.env.dev overlay) |
| `just staging` | Start stack with staging profile |
| `just prod` | Start production stack |
| `just down` | Stop dev stack |
| `just down-staging` | Stop staging stack |
| `just down-prod` | Stop production stack |
| `just logs [service]` | Follow logs |
| `just status` | Container status |
| `just test` | Run root pytest (tests/) |
| `just test-all` | Root tests + `just bridge test` |
| `just lint` | pre-commit run --all-files |
| `just scan` | Security scans (Gitleaks, Trivy) — placeholder |
| `just build` | docker compose build |

## Environment

- `.env` — Copy from `.env.example`; customize domains, passwords, tokens. Required for `just init` and compose.
- `.env.dev` — Overlay for `just dev`; override `IRC_DOMAIN`, `PROSODY_DOMAIN`, etc. for localhost. Required for `just dev`; copy from `.env.dev.example`.

## Per-App Commands (via `just <mod>`)

| Mod | Loads | Example |
|-----|-------|---------|
| `just irc` | apps/unrealircd | `just irc shell`, `just irc reload`, `just irc test` |
| `just xmpp` | apps/prosody | `just xmpp shell`, `just xmpp reload`, `just xmpp adduser` |
| `just web` | apps/web | `just web dev`, `just web build` |
| `just bridge` | apps/bridge | `just bridge test`, `just bridge check` |

## Related

- [apps/atheme/AGENTS.md](apps/atheme/AGENTS.md)
- [apps/bridge/AGENTS.md](apps/bridge/AGENTS.md)
- [apps/prosody/AGENTS.md](apps/prosody/AGENTS.md)
- [apps/unrealircd/AGENTS.md](apps/unrealircd/AGENTS.md)
- [apps/web/AGENTS.md](apps/web/AGENTS.md)
- [docs/AGENTS.md](docs/AGENTS.md)
- [infra/AGENTS.md](infra/AGENTS.md)
- [scripts/AGENTS.md](scripts/AGENTS.md)
- [tests/AGENTS.md](tests/AGENTS.md)
- [README.md](README.md)
