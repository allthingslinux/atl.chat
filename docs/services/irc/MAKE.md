# Makefile Commands

This guide covers the Makefile system used for building, deploying, and managing IRC.atl.chat. The Makefile provides commands for all aspects of the IRC infrastructure.

## Overview

### Command Categories

#### Quick Start Commands

```bash
make up          # Complete setup and start (recommended)
make down        # Stop all services
make restart     # Restart services
make status      # Check service status
```

#### Development Commands

```bash
make test        # Run all tests
make build       # Build containers
make logs        # View service logs
make lint        # Code quality checks
```

## Core Commands

### Service Lifecycle

#### Complete Setup (`make up`)

```bash
# What it does:
# 1. Initializes directories and permissions
# 2. Processes configuration templates
# 3. Builds Docker containers
# 4. Starts all services
# 5. Sets up proper file ownership
make up
```

#### Service Management

```bash
# Start services (assumes setup complete)
make start-only

# Stop all services
make down

# Stop and remove containers/networks
make stop

# Restart all services
make restart

# Force rebuild and restart
make rebuild
```

#### Selective Service Control

```bash
# View specific service logs
make logs-ircd        # UnrealIRCd logs
make logs-atheme      # Atheme logs
make logs-webpanel    # WebPanel logs

# Quick service access
make webpanel         # Open WebPanel info
```

### Building and Development

#### Container Building

```bash
# Build all containers
make build

# Rebuild without cache (clean build)
make rebuild

# Setup only (no start)
make setup
```

#### Development Environment

```bash
# Access development shell
make dev-shell

# View all logs with timestamps
make dev-logs

# Run linting checks
make lint
```

### Testing Framework

#### Test Categories

```bash
# Complete test suite
make test

# Unit tests (no Docker required)
make test-unit

# Integration tests (requires Docker)
make test-integration

# End-to-end tests (full workflow)
make test-e2e

# Protocol compliance tests
make test-protocol

# Performance tests
make test-performance

# Service integration tests
make test-services

# Docker-specific tests
make test-docker
```

#### Specialized Testing

```bash
# Environment validation
make test-env

# IRC functionality tests
make test-irc

# Quick health checks
make test-quick
```

### SSL Certificate Management

#### Certificate Lifecycle

```bash
# One-command SSL setup
make ssl-setup

# Check certificate status
make ssl-status

# Force certificate renewal
make ssl-renew

# View SSL monitoring logs
make ssl-logs

# Stop SSL monitoring
make ssl-stop

# Remove certificates (CAUTION)
make ssl-clean
```

### Module Management

#### Module Operations

```bash
# List available modules
make modules-list

# Show installed modules
make modules-installed

# Generate operator password
make generate-password
```

## Advanced Commands

### System Management

#### Information and Diagnostics

```bash
# Comprehensive help
make help

# System information
make info

# Quick environment check
make test-quick
```

#### Maintenance Operations

```bash
# Clean up containers and images
make clean

# Complete system reset (WARNING: destroys data)
make reset
```

## Command Reference

### Service Management

| Command | Description | Use Case |
|---------|-------------|----------|
| `make up` | Complete setup and start | First-time setup |
| `make down` | Stop all services | Shutdown |
| `make restart` | Restart services | Configuration changes |
| `make status` | Show service status | Monitoring |
| `make logs` | View all logs | Debugging |

### Building

| Command | Description | Use Case |
|---------|-------------|----------|
| `make build` | Build containers | Development |
| `make rebuild` | Clean rebuild | Dependency changes |
| `make setup` | Setup only (no start) | Configuration only |

### Testing

| Command | Description | Test Type |
|---------|-------------|-----------|
| `make test` | Full test suite | Comprehensive |
| `make test-unit` | Unit tests | Fast, isolated |
| `make test-integration` | Integration tests | Service interaction |
| `make test-e2e` | End-to-end tests | Full workflow |
| `make test-protocol` | IRC protocol tests | Compliance |
| `make test-performance` | Performance tests | Load testing |
| `make test-services` | Service tests | Atheme integration |

### SSL Management

| Command | Description | Frequency |
|---------|-------------|-----------|
| `make ssl-setup` | Initial certificate setup | Once |
| `make ssl-status` | Check certificate status | Daily/Weekly |
| `make ssl-renew` | Force renewal | When needed |
| `make ssl-logs` | View SSL logs | Troubleshooting |
| `make ssl-stop` | Stop monitoring | Maintenance |
| `make ssl-clean` | Remove certificates | Emergency |

## Error Handling

### Common Issues

#### Permission Errors

```bash
# Symptom: "Permission denied"
# Solution: Check PUID/PGID in .env
make up  # Automatically fixes permissions

# Manual fix
export PUID=$(id -u)
export PGID=$(id -g)
```

#### Build Failures

```bash
# Symptom: "Build failed"
# Solution: Clean rebuild
make rebuild

# Check build logs
docker compose build --progress=plain unrealircd
```

#### Service Won't Start

```bash
# Check service status
make status

# View specific logs
make logs-ircd

# Validate configuration
make test-env
```

### Debug Mode

#### Enable Verbose Output

```bash
# Add debug flags
DEBUG=1 make up

# Verbose SSL operations
VERBOSE=1 make ssl-setup
```

#### Manual Command Execution

```bash
# Run commands manually
docker compose up -d
docker compose logs -f

# Check environment
env | grep -E "(PUID|PGID|VERSION)"
```

## Best Practices

### Usage Guidelines

#### Development Workflow

```bash
# Daily development cycle
make up          # Start environment
# Make changes
make rebuild     # Test changes
make test        # Validate
make down        # Clean shutdown
```

#### Production Deployment

```bash
# Careful production updates
make test        # Full validation
make up          # Deploy changes
make status      # Verify health
```

### Security Considerations

#### Access Control

```bash
# Secure file permissions
chmod 600 .env cloudflare-credentials.ini

# Use secure passwords
make generate-password
```

## Related Documentation

- [README.md](../README.md) - Quick start guide
- [DOCKER.md](DOCKER.md) - Container setup details
- [CONFIG.md](CONFIG.md) - Configuration management
- [SSL.md](SSL.md) - SSL certificate management
- [UNREALIRCD.md](UNREALIRCD.md) - IRC server configuration
