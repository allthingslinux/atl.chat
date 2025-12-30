# Development Guide

This guide covers the development workflow and local setup for IRC.atl.chat.

## Prerequisites

- **Docker & Docker Compose**: Container runtime
- **Git**: Version control
- **Modern shell**: Bash/Zsh with standard Unix tools
- **Code editor**: VS Code, Vim, Emacs, etc.

## Local Setup

### Clone Repository
```bash
# Clone with SSH (recommended)
git clone git@github.com:allthingslinux/irc.atl.chat.git
cd irc.atl.chat

# Or with HTTPS
git clone https://github.com/allthingslinux/irc.atl.chat.git
cd irc.atl.chat
```

### Environment Configuration
```bash
# Copy environment template
cp env.example .env

# Edit for local development
vim .env

# Required for development:
PUID=$(id -u)
PGID=$(id -g)
IRC_DOMAIN=localhost
IRC_ROOT_DOMAIN=localhost
LETSENCRYPT_EMAIL=dev@localhost
```

### Development Startup
```bash
# Start full development environment
make up

# Or start with debug logging
DEBUG=1 make up

# Verify services are running
make status
```

### Development URLs
- **IRC Server**: `localhost:6697` (TLS)
- **WebPanel**: `http://localhost:8080`
- **JSON-RPC API**: `localhost:8600`
- **WebSocket**: `localhost:8000`

## Development Workflow

### Branching Strategy
```bash
# Create feature branch
git checkout -b feature/my-feature

# Create bug fix branch
git checkout -b bugfix/issue-number

# Create documentation branch
git checkout -b docs/update-guide
```

### Making Changes
```bash
# Start development environment
make up

# Make your changes
# Edit configuration files, scripts, etc.

# Test changes
make test

# Rebuild if needed
make rebuild

# Check service status
make status
```

### Testing
```bash
# Run all tests
make test

# Run specific test categories
make test-unit
make test-integration
make test-e2e

# Quick environment check
make test-quick
```

## Configuration Development

### Template Changes
```bash
# Edit configuration templates
vim src/backend/unrealircd/conf/unrealircd.conf.template
vim src/backend/atheme/conf/atheme.conf.template

# Regenerate configurations
make build

# Restart services
make restart
```

### Environment Variables
```bash
# Add new variables to env.example
vim env.example

# Update .env
vim .env

# Test configuration
make test-env
```

## Docker Development

### Container Debugging
```bash
# Access UnrealIRCd container
docker compose exec unrealircd sh

# Access Atheme container
docker compose exec atheme sh

# Check container logs
docker compose logs unrealircd
docker compose logs atheme
```

### Container Rebuilding
```bash
# Rebuild specific service
docker compose build unrealircd

# Rebuild all services
make rebuild

# Clean rebuild
docker compose build --no-cache
```

## Code Quality

### Linting
```bash
# Run linting checks
make lint

# Check specific files
yamllint compose.yaml
shellcheck scripts/*.sh
```

### Testing
```bash
# Run test suite
make test

# Run specific tests
uv run pytest tests/unit/
uv run pytest tests/integration/
```

## Contributing

### Pull Request Process
1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/my-feature`
3. **Make changes**: Follow coding standards
4. **Test changes**: `make test`
5. **Commit changes**: `git commit -m "Add feature"`
6. **Push branch**: `git push origin feature/my-feature`
7. **Create pull request**

### Code Standards
- **Shell scripts**: Use `shellcheck` for validation
- **YAML files**: Use `yamllint` for validation
- **Documentation**: Update relevant docs for changes
- **Testing**: Add tests for new features

## Debugging

### Enable Debug Mode
```bash
# Debug environment setup
DEBUG=1 make up

# Verbose SSL operations
VERBOSE=1 make ssl-setup

# Debug configuration processing
DEBUG=1 ./scripts/prepare-config.sh
```

### Log Analysis
```bash
# View all logs
make logs

# View specific service logs
make logs-ircd
make logs-atheme
make logs-webpanel

# Follow logs in real-time
docker compose logs -f
```

## Common Development Tasks

### Adding New Modules
```bash
# Edit module list
vim src/backend/unrealircd/third-party-modules.list

# Rebuild container
make rebuild

# Test module installation
make modules-installed
```

### SSL Development
```bash
# Check SSL status
make ssl-status

# Force SSL renewal
make ssl-renew

# View SSL logs
make ssl-logs
```

### Configuration Changes
```bash
# Edit templates
vim src/backend/*/conf/*.template

# Regenerate configs
make build

# Restart services
make restart
```

## Related Documentation

- [CONFIG.md](CONFIG.md) - Configuration management
- [TESTING.md](TESTING.md) - Testing framework
- [MAKE.md](MAKE.md) - Build automation
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions