# atl.chat

Unified chat infrastructure for All Things Linux, supporting IRC, XMPP, and web protocols.

## Architecture

This monorepo contains three core services and bridge infrastructure:

```
apps/
├── irc/        UnrealIRCd + Atheme services
├── xmpp/       Prosody XMPP server
├── web/        Next.js web application
└── bridge/     Protocol bridges (IRC ↔ XMPP)
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for web app)
- pnpm 9+ (for web app)
- just (optional, for task running)

### Setup

```bash
# Clone and install
git clone https://github.com/allthingslinux/atl.chat.git
cd atl.chat
cp .env.example .env

# Edit .env with your configuration
nano .env

# Start all services
docker compose up -d

# Or use just
just up
```

### Development

```bash
# XMPP (with dev tools: Adminer, Dozzle, Converse.js)
cd apps/prosody
docker compose --profile dev up -d

# IRC
cd apps/unrealircd
docker compose up -d

# Web app
cd apps/web
pnpm install
pnpm dev
```

## Services

### IRC (`apps/unrealircd`, `apps/atheme`, `apps/webpanel`)

UnrealIRCd 6.x with Atheme services.

**Ports**: 6697 (TLS), 6900 (server linking), 8000 (WebSocket)
**Services**: NickServ, ChanServ, OperServ, MemoServ, BotServ
**Management**: Web panel on port 8080

```bash
# Common tasks
just irc logs          # View logs
just irc shell         # Access container
just irc reload        # Reload config
```

See [`docs/services/irc/`](docs/services/irc/) for detailed documentation.

### XMPP (`apps/prosody`)

Prosody XMPP server with PostgreSQL backend.

**Ports**: 5222 (C2S), 5269 (S2S), 5280 (HTTP/BOSH), 5281 (HTTPS)
**Database**: PostgreSQL 17
**TURN**: Coturn for audio/video calls

```bash
# Common tasks
just xmpp up           # Start with dev tools
just xmpp up-prod      # Production mode
just xmpp logs         # View logs
just xmpp shell        # Access Prosody shell
```

**Development tools** (with `--profile dev`):
- Adminer (database UI) on port 8081
- Dozzle (log viewer) on port 8082
- Converse.js (web client) on port 8083

See [`docs/services/xmpp/`](docs/services/xmpp/) for detailed documentation.

### Web (`apps/web`)

Next.js 15 application with Turborepo.

**Port**: 3000 (development)
**Stack**: React, TypeScript, Tailwind CSS

```bash
cd apps/web
pnpm dev
```

See [`docs/services/web/`](docs/services/web/) for detailed documentation.

### Bridges (`apps/bridge`)

Protocol bridges for cross-platform communication.

- **Biboumi**: IRC gateway for XMPP clients
- **Matterbridge**: Multi-protocol relay

## Task Running

This project uses [just](https://github.com/casey/just) for task orchestration:

```bash
# Root-level commands
just up              # Start all services
just down            # Stop all services
just logs            # View all logs

# Service-specific commands
just irc <task>      # IRC tasks
just xmpp <task>     # XMPP tasks
just web <task>      # Web tasks

# List all available tasks
just --list
```

## Environment Variables

All configuration is managed through a single `.env` file at the repository root.

```bash
cp .env.example .env
```

Key variables:
- **Database**: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- **TURN**: `TURN_SECRET`, `TURN_REALM`, `TURN_DOMAIN`
- **SSL**: `LETSENCRYPT_EMAIL`, `PROSODY_DOMAIN`
- **IRC**: `IRC_DOMAIN`, `IRC_NETWORK_NAME`, `IRC_OPER_PASSWORD`

See [`.env.example`](.env.example) for complete documentation.

## Docker Compose Profiles

Services use profiles for environment-specific configurations:

```bash
# Production (default)
docker compose up -d

# Development (includes debug tools)
docker compose --profile dev up -d

# Certificate issuance
docker compose --profile cert-issue up atl-xmpp-certbot
```

## Networking

All services communicate via the `atl-chat` Docker network:

```bash
# Create network (if not exists)
docker network create atl-chat

# Services automatically join on startup
```

For inter-host communication, Tailscale is used (configured separately).

## Documentation

- **Infrastructure**: [`docs/infra/`](docs/infra/)
  - [Containerization](docs/infra/containerization.md)
  - [Networking](docs/infra/networking.md)
  - [SSL/TLS](docs/infra/ssl.md)

- **Services**: [`docs/services/`](docs/services/)
  - [IRC Documentation](docs/services/irc/)
  - [XMPP Documentation](docs/services/xmpp/)
  - [Web Documentation](docs/services/web/)

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Run tests: `just test`
5. Commit using conventional commits: `git commit -m "feat: add feature"`
6. Push and open a pull request

## License

Copyright 2025 All Things Linux and Contributors

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

Some components use different licenses; refer to their respective documentation.
