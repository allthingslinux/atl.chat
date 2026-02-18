# Configuration System

This guide covers the configuration management system for IRC.atl.chat, including template processing, environment variables, and automated configuration generation.

## Overview

### Configuration Architecture

IRC.atl.chat uses a template-based configuration system:

```
Configuration Flow:
├── env.example          - Template with defaults
├── .env                 - User configuration
├── *.template           - Configuration templates
├── envsubst             - Variable substitution
└── *.conf               - Generated configurations
```

### Key Principles

- **Template-driven**: All configuration from templates
- **Environment-based**: Variables from `.env` file
- **Automated generation**: No manual config editing
- **Version control safe**: Templates committed, configs ignored
- **Validation**: Automated config checking

## Environment Configuration

### .env File Structure

The `.env` file is the central configuration point:

```bash
# =============================================================================
# IRC.atl.chat Environment Configuration
# =============================================================================

# Core system settings
UNREALIRCD_VERSION=6.2.0.1
PUID=1000
PGID=1000
TZ=UTC

# Network identity
IRC_DOMAIN=irc.atl.chat
IRC_ROOT_DOMAIN=atl.chat
IRC_NETWORK_NAME=atl.chat

# Security settings
IRC_OPER_PASSWORD='$argon2id$...'
LETSENCRYPT_EMAIL=admin@atl.chat

# Service configuration
ATHEME_SEND_PASSWORD=secure_password_here
WEBPANEL_RPC_PASSWORD=admin_password
```

### Environment Variable Categories

#### System Configuration
```bash
# Container user/group IDs (match host user)
PUID=1000                    # Host user ID
PGID=1000                    # Host group ID
TZ=UTC                       # System timezone

# Software versions
UNREALIRCD_VERSION=6.2.0.1   # IRC server version
```

#### Network Configuration
```bash
# Domain and network identity
IRC_DOMAIN=irc.atl.chat           # Server hostname
IRC_ROOT_DOMAIN=atl.chat          # Base domain
IRC_NETWORK_NAME=atl.chat         # Network name

# Port configuration
IRC_TLS_PORT=6697                # IRC over TLS
IRC_SERVER_PORT=6900             # Server linking
IRC_RPC_PORT=8600                # JSON-RPC API
IRC_WEBSOCKET_PORT=8000          # WebSocket IRC
```

#### Security Configuration
```bash
# Authentication
IRC_OPER_PASSWORD='$argon2id$...'  # IRC operator password
LETSENCRYPT_EMAIL=admin@domain.com # SSL certificate email

# Service passwords
ATHEME_SEND_PASSWORD=password     # Atheme-IRCd communication
ATHEME_RECEIVE_PASSWORD=password  # Atheme-IRCd communication
IRC_SERVICES_PASSWORD=password    # Services password
```

### Environment File Management

#### Creating .env File
```bash
# Copy template
cp env.example .env

# Edit with your values
vim .env

# Secure permissions
chmod 600 .env
```

#### Environment Validation
```bash
# Validate .env syntax
bash -n .env

# Test variable substitution
env | grep IRC_
```

## Template System

### Template Processing

#### Template Files
Configuration templates use environment variable substitution:

```bash
# Template syntax
${VARIABLE_NAME}
${VARIABLE_NAME:-default_value}

# Generated output
actual_value
default_value (if VARIABLE_NAME not set)
```

#### Processing Pipeline
```bash
# 1. Read template
cat unrealircd.conf.template

# 2. Substitute variables
envsubst < unrealircd.conf.template > unrealircd.conf

# 3. Set permissions
chmod 644 unrealircd.conf
```

### Template Locations

#### UnrealIRCd Templates
```
apps/unrealircd/config/
├── unrealircd.conf.template     # Main server config (modules inlined)
├── operclass.default.conf       # Operator classes
└── aliases/atheme.conf          # Service aliases
```

#### Atheme Templates
```
apps/atheme/config/
└── atheme.conf.template         # Services configuration
```

### Template Examples

#### UnrealIRCd Main Config
```c
me {
    name "${IRC_DOMAIN}";
    info "${IRC_NETWORK_NAME} IRC Server";
};

admin {
    "${IRC_ADMIN_NAME}";
    "admin";
    "${IRC_ADMIN_EMAIL}";
};

listen {
    ip *;
    port ${IRC_TLS_PORT};
    options { tls; };
};
```

#### Atheme Services Config
```c
serverinfo {
    name = "${ATHEME_SERVER_NAME}";
    uplink = "127.0.0.1";
    recontime = ${ATHEME_RECONTIME};
};

uplink {
    send_password = "${ATHEME_SEND_PASSWORD}";
    receive_password = "${ATHEME_RECEIVE_PASSWORD}";
    port = ${ATHEME_UPLINK_PORT};
};
```

## Configuration Generation

### Automated Processing

#### Build-time Generation
```bash
# Triggered by make up
# Configuration is processed automatically during container build

# What happens:
# 1. Templates are processed with envsubst
# 2. Generated .conf files are created
# 3. Proper permissions are set
```

#### Manual Generation
```bash
# Process specific template
export IRC_DOMAIN=irc.example.com
envsubst < template.conf > generated.conf
```

### Generated Files

#### Gitignore Pattern
Generated configurations are automatically ignored:

```gitignore
# Generated configurations
apps/unrealircd/config/*.conf
apps/atheme/config/*.conf
!apps/unrealircd/config/*.template
!apps/atheme/config/*.template
!apps/unrealircd/config/modules.*.conf
!apps/atheme/config/modules.*.conf
!apps/unrealircd/config/operclass.*.conf
!apps/atheme/config/operclass.*.conf
```

#### File Permissions
```bash
# Configuration files
-rw-r--r--  644 *.conf

# Credential files
-rw-------  600 .env
-rw-------  600 cloudflare-credentials.ini
```

## Validation and Testing

### Configuration Validation

#### Syntax Checking
```bash
# UnrealIRCd config validation
unrealircd -c /path/to/unrealircd.conf

# Atheme config validation
atheme-services -c /path/to/atheme.conf
```

#### Environment Validation
```bash
# Test environment setup
make test-env

# Check variable formats manually
grep -E "^[A-Z_]+=" .env
```

### Testing Configurations

#### Dry Run Testing
```bash
# Test UnrealIRCd config
docker run --rm -v $(pwd)/apps/unrealircd/config:/config \
    unrealircd unrealircd -c /config/unrealircd.conf -t

# Test Atheme config
docker run --rm -v $(pwd)/apps/atheme/config:/config \
    atheme atheme-services -c /config/atheme.conf -n
```

#### Runtime Testing
```bash
# Start with test config
make test-env

# Validate service startup
make test-irc
```

## Security Considerations

### Secret Management

#### Password Storage
```bash
# Hashed passwords (IRC operators)
IRC_OPER_PASSWORD='$argon2id$v=19$m=6144,t=2,p=2$salt$hash'

# Service passwords (plaintext for communication)
ATHEME_SEND_PASSWORD=secure_random_string
```

#### File Permissions
```bash
# Environment file (owner read/write only)
chmod 600 .env

# Generated configs (world readable)
chmod 644 *.conf

# SSL certificates (readable by services)
chmod 644 server.cert.pem
chmod 644 server.key.pem
```

### Access Control

#### Configuration Access
- `.env` file contains sensitive data
- Templates are safe for version control
- Generated configs are runtime-only

#### Audit Logging
```bash
# Log configuration changes
echo "$(date): Config regenerated by $(whoami)" >> config-audit.log

# Track template modifications
git log --oneline apps/unrealircd/config/*.template apps/atheme/config/*.template
```

## Configuration Management

### Environment Setup
```bash
# Copy template to create your configuration
cp env.example .env

# Edit with your values
vim .env

# Secure the file
chmod 600 .env
```

## Advanced Configuration

### Dynamic Configuration

#### Runtime Configuration Changes
```bash
# Modify .env
vim .env

# Regenerate configs
make build

# Restart services
make restart
```

#### Configuration Reloading
Some configuration changes require service restart:

```bash
# Restart services to apply changes
make restart
```

### Template Extensions

#### Custom Templates
```bash
# Create custom template
cp unrealircd.conf.template custom.conf.template

# Add custom variables
echo 'custom_setting = "${CUSTOM_VAR}"' >> custom.conf.template

# Generate custom config
envsubst < custom.conf.template > custom.conf
```

#### Template Includes
```c
// Include additional config files
include "custom.conf";
// Modules are inlined in unrealircd.conf.template
```

### Configuration Overrides

#### Environment Overrides
```bash
# Override at runtime
IRC_DOMAIN=dev.irc.atl.chat make up

# Temporary overrides
export IRC_TLS_PORT=6698
make up
```

#### Service-Specific Configs
```yaml
# Docker Compose overrides
environment:
  - IRC_DOMAIN=staging.irc.atl.chat
  - IRC_TLS_PORT=6698
```

## Troubleshooting

### Common Configuration Issues

#### Template Processing Errors
```bash
# Missing variables
envsubst < template.conf
# Error: bad substitution

# Check required variables
echo ${REQUIRED_VAR:?"Variable not set"}

# Validate .env file
bash -n .env
```

#### Permission Errors
```bash
# File permission issues
ls -la .env
# Should be: -rw------- owner

# Fix permissions
chmod 600 .env

# Check user alignment
echo "PUID: $(id -u), PGID: $(id -g)"
```

#### Configuration Syntax Errors
```bash
# UnrealIRCd syntax check
unrealircd -c unrealircd.conf 2>&1 | head -20

# Atheme syntax check
atheme-services -c atheme.conf -n

# Common errors:
# - Missing semicolons
# - Unclosed braces
# - Invalid variable names
```

#### Variable Substitution Issues
```bash
# Debug variable values
env | grep IRC_

# Test substitution
echo "Domain: ${IRC_DOMAIN}"
echo "Port: ${IRC_TLS_PORT:-6697}"

# Check for special characters
grep -n '[^a-zA-Z0-9_]' .env
```

### Debug Procedures

#### Enable Debug Logging
```bash
# Add debug variables
DEBUG=1
VERBOSE=1

# Run with debug output
make up

# Check logs for config processing
make logs | grep -i config
```

#### Configuration Validation
```bash
# Validate all generated configs
find apps/unrealircd apps/atheme -name "*.conf" -exec echo "Checking {}" \; \
    -exec unrealircd -c {} -t \; 2>/dev/null || echo "Invalid: {}"
```

#### Recovery Procedures
```bash
# Restore from backup
cp backup/.env .env
cp backup/*.template apps/unrealircd/config/; cp backup/*.template apps/atheme/config/

# Regenerate configurations
make build

# Test configuration
make test-env
```

## Backup and Recovery

### Configuration Backups

#### Automated Backups
```bash
# Backup .env file
cp .env backup/env-$(date +%Y%m%d).backup

# Backup templates
tar czf backup/templates-$(date +%Y%m%d).tar.gz \
    apps/unrealircd/config/*.template apps/atheme/config/*.template
```

#### Version Control
```bash
# Templates are version controlled
git add apps/unrealircd/config/*.template apps/atheme/config/*.template
git commit -m "Update configuration templates"

# .env is ignored (contains secrets)
echo ".env" >> .gitignore
```

### Recovery Procedures

#### Configuration Recovery
```bash
# Restore .env
cp backup/env-latest.backup .env

# Restore templates
tar xzf backup/templates-latest.tar.gz

# Regenerate configs
make build

# Test recovery
make test-env
```

#### Emergency Config Generation
```bash
# Generate minimal config for testing
export IRC_DOMAIN=localhost
export IRC_TLS_PORT=6697
export IRC_ADMIN_NAME="Emergency Admin"

# Create basic .env
cat > .env << EOF
IRC_DOMAIN=localhost
IRC_TLS_PORT=6697
IRC_ADMIN_NAME=Emergency Admin
IRC_ADMIN_EMAIL=admin@localhost
EOF

# Regenerate configs
make build
```

## Maintenance

### Regular Tasks

#### Configuration Audits
```bash
# Check for outdated templates
find apps/unrealircd apps/atheme -name "*.template" -newer *.conf

# Validate all configurations
make test-env

# Review .env for security
grep -E "(PASSWORD|SECRET)" .env
```

#### Template Updates
```bash
# Update templates from upstream
git pull origin main

# Check for template changes
git diff apps/unrealircd/config/*.template apps/atheme/config/*.template

# Test new templates
make build
make test
```

### Documentation Updates

#### Configuration Documentation
```bash
# Update env.example comments
vim env.example

# Document new variables
echo "# NEW_VAR - Description" >> env.example

# Update this documentation
vim docs/CONFIG.md
```

## Related Documentation

- [README.md](../README.md) - Quick start and basic configuration
- [UNREALIRCD.md](UNREALIRCD.md) - IRC server configuration details
- [ATHEME.md](ATHEME.md) - IRC services configuration
- [SSL.md](SSL.md) - SSL certificate configuration
- [DOCKER.md](DOCKER.md) - Container configuration
- [MAKE.md](MAKE.md) - Build and automation system
- [SECRET_MANAGEMENT.md](SECRET_MANAGEMENT.md) - Secret handling