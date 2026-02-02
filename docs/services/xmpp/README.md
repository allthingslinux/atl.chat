# XMPP Service (Prosody)

This application provides the core XMPP services for the `atl.chat` ecosystem, utilizing Prosody for the server daemon and PostgreSQL for persistence.

> [!IMPORTANT]
> This service is part of the `atl.chat` monorepo. Please refer to the [Root Documentation](../../docs/README.md) for global orchestration, networking, and SSL standards.

## Architecture

| Component | Technology | Purpose |
|-----------|------------|---------|
| XMPP Server | Prosody 0.12.4 | Modern XMPP daemon |
| Database | PostgreSQL 16 | User and message persistence |
| Web Client | ConverseJS | Integrated browser-based chat |

## Quick Start (Monorepo)

```bash
# 1. Access the root directory
cd atl.chat

# 2. Configure variables (see .env.shared.example)
# Service-specific overrides go in apps/xmpp/.env.development

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

## Infrastructure Alignment
- **Networking**: See [Networking Registry](../../docs/infra/networking.md) for XMPP port (5222).
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
xmpp.atl.chat/
├── app/
│   └── config/
│       └── prosody/             # Prosody configuration
├── prosody-modules/             # Community modules
├── web/                         # Web client assets
│   ├── assets/                  # Static files
│   └── conversejs/              # ConverseJS web client
├── scripts/                     # Management scripts
├── config/                      # Service configurations
├── database/                    # Database initialization
├── .runtime/                    # Runtime data
│   ├── certs/                   # SSL certificates
│   ├── logs/                    # Service logs
│   └── db/                      # Database files
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

### Services Not Starting
```bash
make logs
make status
```

### SSL Issues
```bash
make ssl-status
make ssl-logs
```

### Configuration Issues
```bash
make restart
# Check if configuration was generated properly
ls -la app/config/prosody/prosody.cfg.lua

# If configs are missing, regenerate from templates
make dev-build
```

## Development

### Running Tests
```bash
make test
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
