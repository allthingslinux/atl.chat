# atl.chat

Unified chat infrastructure for All Things Linux: IRC, XMPP, web, and protocol bridges.

## Architecture

Monorepo layout:

```
apps/
├── unrealircd/     # UnrealIRCd 6.x server
├── atheme/         # IRC services (NickServ, ChanServ, OperServ, MemoServ)
├── webpanel/       # UnrealIRCd web admin
├── prosody/        # XMPP server
├── web/            # Next.js web application
├── bridge/         # Discord↔IRC↔XMPP bridge (in-repo)
└── gamja/          # IRC web client (planned)
```

Compose fragments in `infra/compose/`:

- `irc.yaml` — UnrealIRCd, Atheme, WebPanel
- `xmpp.yaml` — Prosody
- `cert-manager.yaml` — Lego (Let's Encrypt)
- `bridge.yaml` — Discord↔IRC↔XMPP bridge
- `networks.yaml` — Shared `atl-chat` network

## Quick Start

### Prerequisites

- Docker & Docker Compose
- [just](https://github.com/casey/just) — task runner
- Node.js 20+ & pnpm 9+ — for web app (optional)
- [uv](https://github.com/astral-sh/uv) or Python 3.11+ — for tests (optional)

### Setup

```bash
git clone https://github.com/allthingslinux/atl.chat.git
cd atl.chat

cp .env.example .env
# Edit .env with your domains, passwords, and TLS paths

just init      # Creates data/ dirs, generates config, dev certs
just dev       # Starts stack with dev profile (Dozzle, localhost domains)
```

`just init` runs `scripts/init.sh` and `scripts/prepare-config.sh` to:

- Create `data/irc/`, `data/atheme/`, `data/xmpp/`, `data/certs/`
- Substitute `.env` into UnrealIRCd and Atheme config templates
- Generate dev certs for `irc.localhost` (if missing)

### First Run

```bash
# Development (localhost domains, Dozzle for logs)
just dev

# Production (uses domains from .env)
just prod
```

## Services

### IRC Stack

| Service  | Container        | Ports |
|----------|------------------|-------|
| UnrealIRCd | `atl-irc-server` | 6697 (TLS), 6900 (server), 8600 (RPC), 8000 (WebSocket) |
| Atheme   | `atl-irc-services` | 6901 (uplink), 8081 (HTTPd) |
| WebPanel | `atl-irc-webpanel`  | 8080 |

**Tasks:**

```bash
just irc shell      # Bash into IRC server
just irc reload     # Reload UnrealIRCd config
just irc logs       # View IRC logs
```

See [docs/services/irc/](docs/services/irc/) for full docs.

### XMPP (Prosody)

| Port | Purpose |
|------|---------|
| 5222 | C2S (client) |
| 5269 | S2S |
| 5280 | HTTP/BOSH |
| 5281 | HTTPS |

**Tasks:**

```bash
just xmpp shell     # Bash into Prosody
just xmpp reload    # Reload Prosody
just xmpp adduser   # Add XMPP user
```

See [docs/services/xmpp/](docs/services/xmpp/).

### Web

Next.js 15 app (port 3000):

```bash
just web dev
# or: cd apps/web && pnpm dev
```

### Bridges

Discord↔IRC↔XMPP bridge (in-repo). See [apps/bridge/](apps/bridge/) and `infra/compose/bridge.yaml`.

```bash
just bridge test     # Run bridge tests
just bridge lint     # Ruff check
just bridge format   # Ruff format
just bridge check    # Full check (lint + typecheck + test)
```

## Task Running

```bash
just --list        # All tasks

# Orchestration
just init          # One-time setup
just dev           # Start dev stack
just prod          # Start prod stack
just down          # Stop stack
just logs          # Follow all logs
just status        # Container status

# Build & test
just build         # Build images
just test          # Run pytest
just lint          # pre-commit run --all-files
```

## Data Layout

All persistent data lives under `data/`:

```
data/
├── irc/
│   ├── data/          # UnrealIRCd runtime
│   ├── logs/          # UnrealIRCd logs
│   └── webpanel-data/ # Web panel state
├── atheme/
│   ├── data/          # services.db
│   └── logs/          # atheme.log
├── xmpp/
│   ├── data/          # Prosody SQLite
│   └── uploads/       # File uploads
└── certs/             # TLS certs (Let's Encrypt layout)
    └── live/<domain>/  # fullchain.pem, privkey.pem
```

See [docs/infra/data-structure.md](docs/infra/data-structure.md).

## Environment

Single `.env` at repo root. Copy from `.env.example` and customize:

```bash
cp .env.example .env
```

Key groups:

- **IRC**: `IRC_DOMAIN`, `IRC_NETWORK_NAME`, `IRC_OPER_PASSWORD`, cloak keys
- **TLS**: `IRC_SSL_CERT_PATH`, `IRC_SSL_KEY_PATH` (paths inside container)
- **Atheme**: `ATHEME_SEND_PASSWORD`, `ATHEME_RECEIVE_PASSWORD`, `IRC_SERVICES_PASSWORD`
- **XMPP**: `PROSODY_DOMAIN`, `PROSODY_SSL_*`

Config is generated via `scripts/prepare-config.sh` (run by `just init`). After editing `.env`, rerun:

```bash
./scripts/prepare-config.sh
```

## Profiles

| Profile   | Use case                          |
|-----------|-----------------------------------|
| default   | Production-style (domains from .env) |
| dev       | Dozzle, localhost domains, extra tools |
| staging   | Staging environment               |
| prod      | Production                        |

```bash
docker compose --profile dev up -d
just dev    # Uses .env.dev + dev profile
```

## Documentation

| Area          | Path |
|---------------|------|
| Hub           | [docs/README.md](docs/README.md) |
| Onboarding    | [docs/onboarding/README.md](docs/onboarding/README.md) |
| Architecture  | [docs/architecture/README.md](docs/architecture/README.md) |
| Data layout   | [docs/infra/data-structure.md](docs/infra/data-structure.md) |
| IRC           | [docs/services/irc/](docs/services/irc/) |
| XMPP          | [docs/services/xmpp/](docs/services/xmpp/) |
| Web           | [docs/services/web/](docs/services/web/) |
| Bridges       | [docs/bridges/README.md](docs/bridges/README.md) |

## Contributing

1. Fork and branch: `git checkout -b feat/my-feature`
2. Run `just init` and `just dev`
3. Make changes
4. Run `just test` and `just lint`
5. Commit: `git commit -m "feat: add feature"` (conventional commits)
6. Open a pull request

## License

See [LICENSE](LICENSE).
