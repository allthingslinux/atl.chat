# Management Scripts

This guide covers the management and utility scripts for IRC.atl.chat deployment and operations.

## Overview

IRC.atl.chat includes several management scripts:

```
scripts/
├── init.sh              # System initialization
├── prepare-config.sh    # Configuration processing
└── health-check.sh      # Host-side IRC port health check
```

SSL: Use cert-manager (Lego) via `just irc ssl-setup`. See SSL.md.

## Core Scripts

### Initialization Script (`scripts/init.sh`)

**Purpose**: Initialize the IRC.atl.chat environment and create required directories.

**Usage**:
```bash
# Automatic initialization (called by make up)
./scripts/init.sh

# Manual initialization with debug output
DEBUG=1 ./scripts/init.sh
```

**What it does**:
1. Creates persistent data directories (`data/`, `logs/`)
2. Sets proper ownership for host user
3. Validates environment variables (PUID/PGID)
4. Checks Docker availability

### Configuration Preparation (`scripts/prepare-config.sh`)

**Purpose**: Process template files and generate production configurations.

**Usage**:
```bash
# Process all configuration templates
./scripts/prepare-config.sh

# Process with verbose output
VERBOSE=1 ./scripts/prepare-config.sh
```

**What it does**:
1. Validates `.env` file exists and is readable
2. Processes all `.template` files with `envsubst`
3. Generates `.conf` files from templates
4. Sets proper file permissions

### Health Check (`scripts/health-check.sh`)

**Purpose**: Check if UnrealIRCd is responding on the IRC port.

**Usage**:
```bash
# Check IRC port (default 6697)
./scripts/health-check.sh

# Check specific port
IRC_PORT=6697 ./scripts/health-check.sh
```

**What it does**:
1. Tests connectivity to IRC port
2. Returns exit code 0 (success) or 1 (failure)
3. Used by Docker health checks

## Script Features

### Error Handling
All scripts use proper error handling:
- `set -euo pipefail` for strict error handling
- Proper exit codes
- Clear error messages

### Logging
Scripts provide structured logging:
- Timestamps for all operations
- Clear success/failure messages
- Debug output when `DEBUG=1` is set

### Configuration
Scripts are environment-driven:
- Read from `.env` file
- Use environment variables for configuration
- Support debug and verbose modes

## Usage Examples

### Complete Setup
```bash
# Initialize environment
./scripts/init.sh

# Prepare configurations
./scripts/prepare-config.sh

# Setup SSL certificates
./scripts/ssl-manager.sh issue

# Start services
docker compose up -d

# Check health
./scripts/health-check.sh
```

### Maintenance Tasks
```bash
# Check SSL certificate status
./scripts/ssl-manager.sh check

# Renew certificates if needed
./scripts/ssl-manager.sh renew

# Verify service health
./scripts/health-check.sh
```

### Troubleshooting
```bash
# Debug initialization
DEBUG=1 ./scripts/init.sh

# Verbose configuration processing
VERBOSE=1 ./scripts/prepare-config.sh

# Check SSL with debug output
DEBUG=1 ./scripts/ssl-manager.sh check
```

## Integration with Makefile

The scripts are integrated with the Makefile:

```bash
# These make commands use the scripts internally
make up          # Uses init.sh and prepare-config.sh
make ssl-setup   # Uses ssl-manager.sh issue
make ssl-status  # Uses ssl-manager.sh check
make ssl-renew   # Uses ssl-manager.sh renew
```

## Troubleshooting

### Script Failures
```bash
# Check script permissions
ls -la scripts/

# Make scripts executable
chmod +x scripts/*.sh

# Check environment variables
env | grep -E "(PUID|PGID|IRC_)"
```

### Permission Issues
```bash
# Fix script permissions
chmod +x scripts/*.sh

# Fix data directory permissions
sudo chown -R $(id -u):$(id -g) data/ logs/
```

### Configuration Issues
```bash
# Validate .env file
bash -n .env

# Check required variables
grep -E "(PUID|PGID|IRC_DOMAIN)" .env
```

## Related Documentation

- [MAKE.md](MAKE.md) - Build automation and management commands
- [CONFIG.md](CONFIG.md) - Configuration management
- [SSL.md](SSL.md) - SSL certificate management
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions