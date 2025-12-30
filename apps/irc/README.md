# IRC.atl.chat

Docker-based IRC server with UnrealIRCd, Atheme Services, and automated SSL certificate management.

## Architecture

| Component | Technology | Purpose |
|-----------|------------|---------|
| IRC Server | UnrealIRCd 6.2.0.1 | IRC daemon |
| Services | Atheme 7.2.12 | NickServ, ChanServ, OperServ |
| WebPanel | UnrealIRCd WebPanel | Admin interface |
| SSL/TLS | Let's Encrypt + Cloudflare | Certificate management |
| Container | Docker + Compose | Deployment |

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/allthingslinux/irc.atl.chat
cd irc.atl.chat
cp env.example .env

# 2. Edit configuration
# BE SURE TO READ THIS CAREFULLY AND DOUBLE CHECK ALL VARIABLES
# ATHEME WILL NOT START WITHOUT THE SEND AND RECEIVE PASSWORD SET PROPERLY
vim .env

# 3. Setup Cloudflare DNS credentials
cp cloudflare-credentials.ini.template cloudflare-credentials.ini
chmod 600 cloudflare-credentials.ini
vim cloudflare-credentials.ini  # Add your Cloudflare API token

# 4. Setup SSL certificates (required before starting)
make ssl-setup

# 5. Start services
make up
```

**Note**: SSL setup must be completed before starting services, as UnrealIRCd configuration expects SSL certificates to exist.

## Configuration

### Environment Variables

Copy `env.example` to `.env` and configure:

```bash
# Server Settings
IRC_DOMAIN=irc.atl.chat
# IRC_PORT=6667                    # Disabled - TLS only
IRC_TLS_PORT=6697
IRC_RPC_PORT=8600

# Network Identity
IRC_ROOT_DOMAIN=atl.chat
IRC_NETWORK_NAME=atl.chat
IRC_CLOAK_PREFIX=atl

# Admin Contact
IRC_ADMIN_NAME="Your Admin Name"
IRC_ADMIN_EMAIL=admin@yourdomain.com

# SSL/TLS
LETSENCRYPT_EMAIL=admin@yourdomain.com

# Services
ATHEME_SERVER_NAME=services.atl.chat
ATHEME_UPLINK_HOST=irc.atl.chat
ATHEME_UPLINK_PORT=6900
ATHEME_SEND_PASSWORD=your-services-password
ATHEME_RECEIVE_PASSWORD=your-services-password
```

## Configuration Workflow

Configuration files are automatically generated from templates using your `.env` file:

- **Templates**: `src/backend/*/conf/*.template` files
- **Generated**: `src/backend/*/conf/*.conf` files (gitignored)
- **Process**: `envsubst` substitutes variables from `.env` into templates
- **Automation**: `make up` runs `init.sh` and `prepare-config.sh` automatically

**Never edit the `.conf` files directly** - they will be overwritten. Always modify the `.env` file and run `make up` to regenerate.

## Commands

### Service Management
```bash
make up             # Start all services
make down           # Stop all services
make restart        # Restart services
make status         # Check service status
make logs           # View all logs
```

### Development
```bash
make build          # Build containers
make rebuild        # Rebuild from scratch
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

### Utilities
```bash
make generate-password    # Generate IRC operator password
make modules-list         # List available modules
make modules-installed    # Show installed modules
```

## Project Structure

```
irc.atl.chat/
├── src/
│   ├── backend/
│   │   ├── unrealircd/          # IRC server
│   │   └── atheme/              # IRC services
│   └── frontend/
│       ├── webpanel/            # Admin interface
│       └── gamja/               # Web client (optional)
├── scripts/                     # Management scripts
├── docs/                        # Documentation
├── data/                        # Persistent data
├── logs/                        # Service logs
└── tests/                       # Test suite
```

## Ports

| Port | Protocol | Service | Purpose |
|------|----------|---------|---------|
| ~~6667~~ | ~~IRC~~ | ~~UnrealIRCd~~ | ~~Standard IRC~~ (disabled - TLS only) |
| 6697 | IRC+TLS | UnrealIRCd | Encrypted IRC |
| 6900 | IRC+TLS | UnrealIRCd | Server links |
| 6901 | IRC | UnrealIRCd | Atheme services (localhost) |
| 8600 | HTTP | UnrealIRCd | JSON-RPC API |
| 8000 | WebSocket | UnrealIRCd | WebSocket IRC |
| 8080 | HTTP | WebPanel | Admin interface |

## Usage

### Connect to IRC

```bash
# TLS connection (required)
irc irc.atl.chat:6697

# Note: Plaintext connections are disabled for security
# All clients must use SSL/TLS on port 6697
```

### WebPanel

- URL: `http://your-server:8080`
- Purpose: IRC server management

### IRC Services

- **NickServ**: `/msg NickServ REGISTER password email`
- **ChanServ**: `/msg ChanServ REGISTER #channel`
- **OperServ**: Administrative services

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
ls -la src/backend/unrealircd/conf/unrealircd.conf
ls -la src/backend/atheme/conf/atheme.conf

# If configs are missing, regenerate from templates
make build
```

## Development

### Running Tests
```bash
make test
```

#### Test Structure
IRC.atl.chat uses a comprehensive testing framework organized by testing level (traditional approach):

- **`tests/unit/`** - Unit tests for individual components and functions
  - Configuration validation, Docker client testing, environment setup
- **`tests/integration/`** - Integration tests using controlled IRC servers
  - `test_protocol.py` - IRC protocol compliance (RFC1459, RFC2812)
  - `test_clients.py` - Client library integration (pydle, python-irc)
  - `test_services.py` - Service integration (NickServ, ChanServ, Atheme)
  - `test_monitoring.py` - Server monitoring and RPC functionality
  - `test_performance.py` - Performance and load testing
  - `test_infrastructure.py` - Infrastructure and deployment tests
  - `test_irc_functionality.py` - General IRC server functionality
- **`tests/e2e/`** - End-to-end workflow tests
- **`tests/protocol/`** - Basic IRC message protocol tests (unit-level)
- **`tests/legacy/integration/`** - Legacy integration tests (deprecated, kept for reference)

All integration tests use a **controller pattern** inspired by [irctest](https://github.com/progval/irctest), providing controlled IRC server instances, service integration, and comprehensive protocol validation.

### Linting
```bash
make lint
```

### Building
```bash
make build
```

## Documentation

### 🚀 Getting Started
- [Quick Start](README.md#quick-start) - Basic installation and setup
- [Configuration](README.md#configuration) - Environment variables and settings
- [Troubleshooting](./docs/TROUBLESHOOTING.md) - Common issues and solutions

### 🏗️ Core Components
- [UnrealIRCd Server](./docs/UNREALIRCD.md) - IRC server configuration and management
- [Atheme Services](./docs/ATHEME.md) - IRC services (NickServ, ChanServ, etc.)
- [Modules](./docs/MODULES.md) - UnrealIRCd module system and third-party extensions
- [WebPanel](./docs/WEBPANEL.md) - Web-based administration interface

### 🐳 Infrastructure
- [Docker Setup](./docs/DOCKER.md) - Containerization, volumes, and networking
- [Makefile Commands](./docs/MAKE.md) - Build automation and management commands
- [Configuration](./docs/CONFIG.md) - Template system and environment variables
- [CI/CD Pipeline](./docs/CI_CD.md) - GitHub Actions workflows and automation
- [Testing](./docs/TESTING.md) - Comprehensive test suite and framework

### 🔒 Security & Operations
- [SSL Certificates](./docs/SSL.md) - Let's Encrypt automation and certificate management
- [Secret Management](./docs/SECRET_MANAGEMENT.md) - Passwords, API tokens, and security practices
- [User Modes](./docs/USERMODES.md) - IRC user mode reference and configuration
- [Backup & Recovery](./docs/BACKUP_RECOVERY.md) - Data protection and disaster recovery

### 🔌 APIs & Integration
- [API Reference](./docs/API.md) - JSON-RPC API and WebSocket support
- [Scripts](./docs/SCRIPTS.md) - Management and utility scripts

### 🛠️ Development
- [Development Guide](./docs/DEVELOPMENT.md) - Local setup, contribution guidelines, and workflow

## License

MIT License - see [LICENSE](LICENSE) for details.
