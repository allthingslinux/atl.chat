# XMPP Service (Prosody)

This application provides the core XMPP services for the `atl.chat` ecosystem, utilizing Prosody for the server daemon and PostgreSQL for persistence.

> [!IMPORTANT]
> This service is part of the `atl.chat` monorepo. Please refer to the [Root Documentation](../../docs/README.md) for global orchestration, networking, and SSL standards.

## Architecture

| Component | Technology | Purpose |
|-----------|------------|---------|
| XMPP Server | Prosody 13.0.4 | Modern XMPP daemon |
| Database | PostgreSQL 16 | User and message persistence |
| Web Client | ConverseJS | Integrated browser-based chat |

## Quick Start (Monorepo)

```bash
# 1. Access the root directory
cd atl.chat

# 2. Configure variables (see .env.shared.example)
# Service-specific overrides go in apps/prosody/.env.development

# 3. Start the XMPP stack
just profile=xmpp up
```

## Commands

Use the root `justfile` for most operations:

| Action | Command |
|--------|---------|
| Start XMPP | `just profile=xmpp up` |
| View Logs | `just logs atl-xmpp-server` |
| XMPP Shell | `just shell atl-xmpp-server` |
| Status | `just status` |
| Add user | `just xmpp adduser user@domain` |
| Delete user | `just xmpp deluser user@domain` |
| Reload config | `just xmpp reload` |
| Check (all) | `just xmpp check` |
| Check config | `just xmpp check-config` |
| Check certs | `just xmpp check-certs` |
| Check connectivity | `just xmpp check-connectivity` |
| Check disabled | `just xmpp check-disabled` |
| Check DNS | `just xmpp check-dns` |
| Check features | `just xmpp check-features` |
| Check TURN | `just xmpp check-turn` or `just xmpp check-turn stun.example.com` |

## Admin User Setup

Prosody requires an admin account to be registered before you can use admin features (HTTP admin, MUC room creation, etc.). The admin JID is configured via `PROSODY_ADMIN_JID` in `.env` (default: `admin@${PROSODY_DOMAIN}`).

**Create the admin account** after the XMPP stack is running:

```bash
# Using just (recommended)
just xmpp adduser admin@your-domain.tld
# You will be prompted for a password interactively

# Or with password inline (for scripts/automation)
just xmpp adduser admin@your-domain.tld your-secure-password
```

**Using docker exec directly** (e.g. when not using the root justfile):

```bash
# Interactive (prompts for password)
docker compose -f compose.yaml exec atl-xmpp-server prosodyctl adduser admin@your-domain.tld

# Non-interactive (for scripts)
docker compose -f compose.yaml exec atl-xmpp-server bash -c "echo -e 'password\npassword' | prosodyctl adduser admin@your-domain.tld"
```

**Important:** The JID you register must match `PROSODY_ADMIN_JID` in your `.env`. For local development with `PROSODY_DOMAIN=localhost`, use `admin@localhost`.

## User Provisioning (Portal)

Users are provisioned by the [Portal](https://github.com/allthingslinux/portal) via **mod_http_admin_api** (REST API). Self-registration is disabled (`PROSODY_ALLOW_REGISTRATION=false`).

| Module | Purpose |
|--------|---------|
| `mod_http_admin_api` | REST API for user create/delete; Portal calls this to provision XMPP accounts |
| `mod_register` | Kept for password changes (users can change password via XMPP client) |
| `mod_watchregistrations` | Disabled (no in-band registration) |

To allow self-registration (e.g. local dev), set `PROSODY_ALLOW_REGISTRATION=true` in `.env`.

## Infrastructure Alignment

- **Networking**: See [Networking Registry](../../docs/infra/networking.md) for XMPP port (5222).
- **DNS**: See [DNS Configuration](DNS.md) for SRV records and domain setup.
- **SSL**: Terminated at the `atl.network` gateway. See [SSL Strategy](../../docs/infra/ssl.md).
- **Deployment**: Managed via standard `Containerfile` and `compose.yaml`.

### Module Management

```bash
make list-modules          # List available modules
make enable-module         # Enable a module
make update-modules        # Update module collection
```

### Database Operations

```bash
make db-backup            # Backup database
make db-restore           # Restore database
```

## Project Structure

```
apps/prosody/
├── config/                      # Prosody configuration (prosody.cfg.lua)
├── modules.list                 # Community modules (baked into image at build)
├── www/                         # Static files for Prosody http (Converse.js via mod_conversejs at /conversejs)
├── scripts/                     # Management scripts
└── tests/                       # Test suite
```

## Ports

| Port | Protocol | Service | Purpose |
|------|----------|---------|---------|
| 5222 | XMPP | Prosody | Client connections |
| 5269 | XMPP | Prosody | Server-to-server |
| 5223 | XMPP+TLS | Prosody | Direct TLS client |
| 5270 | XMPP+TLS | Prosody | Direct TLS server |
| 5280 | HTTP | Prosody | HTTP upload/admin |
| 5281 | HTTPS | Prosody | HTTPS upload/admin |
| 8080 | HTTP | Web Client | ConverseJS interface |

## Usage

### Connect to XMPP

```bash
# Standard XMPP connection
xmpp-client user@atl.chat

# Web client
# URL: http://your-server:8080
```

### Web Interface

- URL: `http://your-server:8080`
- Purpose: Browser-based XMPP client

### XMPP Services

- **Registration**: Account creation (if enabled)
- **MUC**: Multi-user chat rooms
- **HTTP Upload**: File sharing
- **Push Notifications**: Mobile notifications

## Troubleshooting

### First steps

Run Prosody's sanity checks:

```bash
just xmpp check
```

This runs `prosodyctl check` (config, certs, dns, etc.). Individual checks: `just xmpp check-config`, `just xmpp check-certs`, `just xmpp check-dns`, `just xmpp check-features`, `just xmpp check-connectivity`, `just xmpp check-turn`.

### Services not starting

```bash
just logs atl-xmpp-server
just status
```

### SSL / certificate issues

```bash
just xmpp check-certs
just logs atl-xmpp-server
```

### Configuration issues

```bash
# Verify config exists and was generated
ls -la apps/prosody/config/prosody.cfg.lua

# Regenerate config and restart
just init
docker compose restart atl-xmpp-server
```

### Can't contact other servers (S2S)

- Ensure port 5269 is open (firewall, NAT)
- Verify DNS: `just xmpp check-dns`
- Test connectivity: `telnet yourdomain.com 5269`

## Development

### Running tests

```bash
just test
```

#### Test Structure

XMPP.atl.chat uses a comprehensive testing framework organized by testing level:

- **`tests/unit/`** - Unit tests for individual components
  - Configuration validation, Docker setup, environment testing
- **`tests/integration/`** - Integration tests using controlled XMPP servers
  - `test_protocol.py` - XMPP protocol compliance (RFC6120, RFC6121)
  - `test_clients.py` - Client library integration
  - `test_services.py` - Service integration (MUC, HTTP upload)
  - `test_monitoring.py` - Server monitoring and admin functionality
  - `test_performance.py` - Performance and load testing
  - `test_infrastructure.py` - Infrastructure and deployment tests
- **`tests/e2e/`** - End-to-end workflow tests

### Linting

```bash
make lint
```

### Building

```bash
make dev-build
```

## Documentation

### 🚀 Getting Started

- [Quick Start](README.md#quick-start) - Basic installation and setup
- [Configuration](README.md#configuration) - Environment variables and settings
- [Troubleshooting](./docs/TROUBLESHOOTING.md) - Common issues and solutions

### 🏗️ Core Components

- [Prosody Server](./docs/PROSODY.md) - XMPP server configuration and management
- [Modules](./docs/MODULES.md) - Prosody module system and third-party extensions
- [Web Client](./docs/WEBCLIENT.md) - ConverseJS configuration and customization
- [Database](./docs/DATABASE.md) - PostgreSQL setup and management

### 🐳 Infrastructure

- [DNS Configuration](DNS.md) - SRV records, A records, and domain setup
- [Docker Setup](./docs/DOCKER.md) - Containerization, volumes, and networking
- [Makefile Commands](./docs/MAKE.md) - Build automation and management commands
- [Configuration](./docs/CONFIG.md) - Template system and environment variables
- [CI/CD Pipeline](./docs/CI_CD.md) - GitHub Actions workflows and automation
- [Testing](./docs/TESTING.md) - Comprehensive test suite and framework

### 🔒 Security & Operations

- [SSL Certificates](./docs/SSL.md) - Let's Encrypt automation and certificate management
- [Secret Management](./docs/SECRET_MANAGEMENT.md) - Passwords, API tokens, and security practices
- [Backup & Recovery](./docs/BACKUP_RECOVERY.md) - Data protection and disaster recovery

### 🔌 APIs & Integration

- [API Reference](./docs/API.md) - HTTP API and admin interface
- [Scripts](./docs/SCRIPTS.md) - Management and utility scripts

### 🛠️ Development

- [Development Guide](./docs/DEVELOPMENT.md) - Local setup, contribution guidelines, and workflow

## License

Apache License 2.0
