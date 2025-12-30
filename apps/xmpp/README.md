# XMPP.atl.chat

Docker-based XMPP server with Prosody, PostgreSQL database, and automated SSL certificate management.

## Architecture

| Component | Technology | Purpose |
|-----------|------------|---------|
| XMPP Server | Prosody 0.12.4 | XMPP daemon |
| Database | PostgreSQL 16 | Data persistence |
| Web Client | ConverseJS | Browser-based XMPP client |
| SSL/TLS | Let's Encrypt + Cloudflare | Certificate management |
| Container | Docker + Compose | Deployment |

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/allthingslinux/xmpp.atl.chat
cd xmpp.atl.chat
cp .env.development .env

# 2. Edit configuration
# BE SURE TO READ THIS CAREFULLY AND DOUBLE CHECK ALL VARIABLES
# PROSODY WILL NOT START WITHOUT PROPER DATABASE CREDENTIALS
vim .env

# 3. Setup Cloudflare DNS credentials
cp cloudflare-credentials.ini.template cloudflare-credentials.ini
chmod 600 cloudflare-credentials.ini
vim cloudflare-credentials.ini  # Add your Cloudflare API token

# 4. Setup SSL certificates (required before starting)
make ssl-setup

# 5. Start services
make dev
```

**Note**: SSL setup must be completed before starting services, as Prosody configuration expects SSL certificates to exist.

## Configuration

### Environment Variables

Copy `.env.development` to `.env` and configure:

```bash
# Server Settings
PROSODY_DOMAIN=atl.chat
PROSODY_C2S_PORT=5222
PROSODY_S2S_PORT=5269
PROSODY_C2S_DIRECT_TLS_PORT=5223
PROSODY_S2S_DIRECT_TLS_PORT=5270

# Network Identity
PROSODY_ADMIN_JID=admin@atl.chat
PROSODY_ADMIN_EMAIL=admin@allthingslinux.org

# SSL/TLS
LETSENCRYPT_EMAIL=admin@allthingslinux.org

# Database
PROSODY_DB_DRIVER=PostgreSQL
PROSODY_DB_HOST=xmpp-postgres
PROSODY_DB_PORT=5432
PROSODY_DB_NAME=prosody
PROSODY_DB_USER=prosody
PROSODY_DB_PASSWORD=your-database-password
```

## Configuration Workflow

Configuration files are automatically generated from templates using your `.env` file:

- **Templates**: `app/config/prosody/*.template` files
- **Generated**: `app/config/prosody/*.conf` files (gitignored)
- **Process**: `envsubst` substitutes variables from `.env` into templates
- **Automation**: `make dev` runs configuration generation automatically

**Never edit the `.conf` files directly** - they will be overwritten. Always modify the `.env` file and run `make dev` to regenerate.

## Commands

### Service Management
```bash
make dev            # Start development environment
make prod           # Start production environment
make down           # Stop all services
make restart        # Restart services
make status         # Check service status
make logs           # View all logs
```

### Development
```bash
make dev-build      # Build development containers
make dev-clean      # Clean development environment
make test           # Run test suite
make lint           # Run linting
```

### SSL Management
```bash
make ssl-setup      # Setup SSL certificates
make ssl-status     # Check certificate status
make ssl-renew      # Force renewal
make ssl-logs       # View SSL logs
```

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
