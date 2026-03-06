# atl.chat

Unified chat infrastructure for All Things Linux: IRC, XMPP, web, and protocol bridges.

## Architecture

Monorepo layout:

```
apps/
├── unrealircd/        # UnrealIRCd 6.x server
├── atheme/            # IRC services (NickServ, ChanServ, OperServ, MemoServ)
├── webpanel/          # UnrealIRCd web admin
├── prosody/           # XMPP server
├── web/               # Next.js web application
├── bridge/            # Discord↔IRC↔XMPP bridge (Python, in-repo)
├── thelounge/         # Web IRC client (private mode, WebIRC)
├── obsidianirc/       # Modern IRC web client (custom build)
├── fluux-messenger/   # Fluux XMPP web client (React + Vite, nginx)
├── gamja/             # IRC web client (planned)
└── docs/              # Fumadocs documentation site
```

Compose fragments in `infra/compose/`:

- `irc.yaml` — UnrealIRCd, Atheme, WebPanel
- `xmpp.yaml` — Prosody
- `cert-manager.yaml` — Lego (Let's Encrypt)
- `bridge.yaml` — Discord↔IRC↔XMPP bridge
- `thelounge.yaml` — The Lounge web IRC client
- `obsidianirc.yaml` — ObsidianIRC web client
- `fluux-messenger.yaml` — Fluux XMPP web client
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

# For dev (localhost domains): create overlay from .env.dev.example
cp .env.dev.example .env.dev

just init      # Creates data/ dirs, generates config, dev certs
just dev       # Starts stack with dev profile (Dozzle, localhost domains)
```

`just init` runs `scripts/init.sh` and `scripts/prepare-config.sh` to:

- Create `data/irc/`, `data/atheme/`, `data/xmpp/`, `data/thelounge/`, `data/obsidianirc/`, `data/certs/`
- Substitute `.env` into UnrealIRCd, Atheme, and Bridge config templates
- Generate dev certs for `irc.localhost` (if missing)

`just dev` requires `.env.dev` (copy from `.env.dev.example`); it overrides domains for localhost.

### First Run

```bash
# Development (localhost domains, Dozzle for logs)
just dev

# Production (uses domains from .env)
just prod
```

### First Boot: SRA Bootstrap

After starting the production stack for the first time, you must manually bootstrap the Services Root Administrator (SRA) to avoid being locked out of IRC services:

1. Connect to IRC using your admin account.
2. In the terminal, run: `just irc sra-bootstrap <your_nick>`
3. OperServ will then recognize you as a network administrator.

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
just logs           # Follow logs (root command; use service name to filter)
```

See [docs-old/services/irc/](docs-old/services/irc/) for full docs.

### XMPP (Prosody)

| Port | Purpose |
|------|---------|
| 5222 | C2S (client) |
| 5223 | C2S Direct TLS |
| 5269 | S2S |
| 5270 | S2S Direct TLS |
| 5280 | HTTP/BOSH |
| 5281 | HTTPS |
| 5000 | Proxy65 (file transfer) |

**Tasks:**

```bash
just xmpp shell     # Bash into Prosody
just xmpp reload    # Reload Prosody
just xmpp adduser   # Add XMPP user
```

See [docs-old/services/xmpp/](docs-old/services/xmpp/).

### Web

Next.js 14 app (port 3000):

```bash
just web dev
# or: cd apps/web && pnpm dev
```

### Bridges

Discord↔IRC↔XMPP bridge (Python, in-repo). Multi-presence puppeting, IR-based format conversion, Portal identity integration. See [apps/bridge/](apps/bridge/) and `infra/compose/bridge.yaml`.

```bash
just bridge test       # Run bridge tests
just bridge lint       # Ruff check
just bridge format     # Ruff format
just bridge typecheck  # Basedpyright
just bridge check      # Full check (lint + format + typecheck + test)
```

### The Lounge

Web IRC client (private mode, WebIRC). See [apps/thelounge/](apps/thelounge/).

```bash
just lounge add <name>   # Create user (prompts for password)
just lounge list        # List users
just lounge reset <name> # Reset user password
```

### ObsidianIRC

Modern IRC web client (custom build). See [apps/obsidianirc/](apps/obsidianirc/).

```bash
just obsidianirc rebuild       # Rebuild image
just obsidianirc rebuild-clean # Rebuild without cache
```

### Fluux Messenger

React + Vite XMPP web client by ProcessOne, served via nginx. Connects to Prosody via WebSocket. See [apps/fluux-messenger/](apps/fluux-messenger/).

| Port | Purpose |
|------|---------|
| 8091 | HTTP |
| 8443 | HTTPS |

## Task Running

```bash
just --list        # All tasks

# Orchestration
just init          # One-time setup
just dev           # Start dev stack
just prod          # Start prod stack
just down          # Stop dev stack
just down-prod     # Stop prod stack
just logs [svc]    # Follow logs (optionally for a service)
just status        # Container status

# Build & test
just build         # Build images
just test          # Run root pytest
just test-all      # Root tests + bridge tests
just lint          # pre-commit run --all-files
just scan          # Security scans (Gitleaks, Trivy)
just clean         # Prune unused Docker resources
just prosody-token # Generate Prosody admin API Bearer token
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
│   ├── logs/          # Prosody logs
│   └── uploads/       # File uploads
├── thelounge/         # The Lounge user data
├── obsidianirc/       # ObsidianIRC data (if needed)
└── certs/             # TLS certs (Let's Encrypt layout)
    └── live/<domain>/  # fullchain.pem, privkey.pem
```

See [docs-old/infra/data-structure.md](docs-old/infra/data-structure.md).

## Environment

Single `.env` at repo root. Copy from `.env.example` and customize. For dev, also create `.env.dev` from `.env.dev.example`.

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
| prod      | Production                        |

```bash
docker compose --profile dev up -d
just dev    # Uses .env.dev + dev profile
```

## Documentation

| Area          | Path |
|---------------|------|
| Hub           | [docs-old/README.md](docs-old/README.md) |
| Onboarding    | [docs-old/onboarding/README.md](docs-old/onboarding/README.md) |
| Architecture  | [docs-old/architecture/README.md](docs-old/architecture/README.md) |
| Data layout   | [docs-old/infra/data-structure.md](docs-old/infra/data-structure.md) |
| IRC           | [docs-old/services/irc/](docs-old/services/irc/) |
| XMPP          | [docs-old/services/xmpp/](docs-old/services/xmpp/) |
| Web           | [docs-old/services/web/](docs-old/services/web/) |
| Bridges       | [docs-old/bridges/README.md](docs-old/bridges/README.md) |
| Fumadocs Site | [apps/docs/](apps/docs/) |

## CI/CD

GitHub Actions runs on push to `main`/`develop` and on pull requests:

- Path-based change detection (only affected services are checked)
- Lint, test, and Docker build jobs per service (IRC, XMPP, Web, Bridge)
- Security scans (Gitleaks, Trivy)
- Semantic versioning with automatic changelog on `main` via [semantic-release](https://github.com/semantic-release/semantic-release)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, commit conventions, and code style guidelines.

## License

Apache 2.0 — see [LICENSE](LICENSE).
