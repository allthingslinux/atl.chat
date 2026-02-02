# Documentation Index

Welcome to the IRC.atl.chat documentation! This directory contains comprehensive guides for setting up, configuring, and managing your IRC server infrastructure.

## 🚀 Getting Started

- **[API.md](./API.md)** - JSON-RPC API reference and WebSocket support for IRC server management
- **[CONFIG.md](./CONFIG.md)** - Configuration system overview, environment variables, and template management
- **[DOCKER.md](./DOCKER.md)** - Docker containerization setup, volumes, networking, and deployment
- **[MAKE.md](./MAKE.md)** - Makefile commands reference for build automation and service management
- **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Common issues, solutions, and debugging guides

## 🏗️ Core Components

- **[UNREALIRCD.md](./UNREALIRCD.md)** - UnrealIRCd server configuration, modules, and management
- **[ATHEME.md](./ATHEME.md)** - Atheme IRC services setup (NickServ, ChanServ, OperServ)
- **[MODULES.md](./MODULES.md)** - UnrealIRCd module system, third-party extensions, and customization
- **[USERMODES.md](./USERMODES.md)** - IRC user mode reference and configuration options
- **[WEBPANEL.md](./WEBPANEL.md)** - Web-based administration interface setup and usage

## 🔒 Security & Operations

- **[SSL.md](./SSL.md)** - Let's Encrypt automation, certificate management, and TLS configuration
- **[SECRET_MANAGEMENT.md](./SECRET_MANAGEMENT.md)** - Password management, API tokens, and security best practices
- **[BACKUP_RECOVERY.md](./BACKUP_RECOVERY.md)** - Data protection, backup strategies, and disaster recovery procedures
 setup

## 🛠️ Development & Testing

- **[DEVELOPMENT.md](./DEVELOPMENT.md)** - Local development setup, contribution guidelines, and workflow
- **[TESTING.md](./TESTING.md)** - Comprehensive test suite framework and testing strategies
- **[CI_CD.md](./CI_CD.md)** - GitHub Actions workflows, automation, and deployment pipelines

## 🔧 Utilities & Scripts

- **[SCRIPTS.md](./SCRIPTS.md)** - Management scripts, utilities, and automation tools

## 📋 Project Management

- **[TODO.md](./TODO.md)** - Project roadmap, planned features, and development priorities

## 📁 Examples

The `examples/` directory contains configuration templates and examples:

- **[examples/atheme/](./examples/atheme/)** - Atheme services configuration examples
  - `atheme.conf.example` - Main Atheme configuration template
  - `atheme.motd.example` - Message of the day template
- **[examples/unrealircd/](./examples/unrealircd/)** - UnrealIRCd configuration examples
  - `unrealircd.conf` - Main server configuration
  - `aliases/` - Service alias configurations
  - `examples/` - Multi-language configuration examples
  - `help/` - Help system configurations
  - `modules.*.conf` - Module configuration files
  - `tls/` - TLS/SSL certificate examples

## Quick Navigation

### For New Users
Start with: [CONFIG.md](./CONFIG.md) → [DOCKER.md](./DOCKER.md) → [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

### For Administrators
Focus on: [UNREALIRCD.md](./UNREALIRCD.md) → [ATHEME.md](./ATHEME.md) → [MONITORING.md](./MONITORING.md)

### For Developers
Check out: [DEVELOPMENT.md](./DEVELOPMENT.md) → [TESTING.md](./TESTING.md) → [API.md](./API.md)

### For Security
Review: [SSL.md](./SSL.md) → [SECRET_MANAGEMENT.md](./SECRET_MANAGEMENT.md) → [BACKUP_RECOVERY.md](./BACKUP_RECOVERY.md)

## Contributing to Documentation

When adding or updating documentation:

1. Follow the existing structure and naming conventions
2. Include clear examples and code snippets
3. Update this README.md when adding new documentation files
4. Test all commands and configurations before documenting them
5. Use descriptive headings and maintain consistent formatting

## Need Help?

- Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues
- Review the main project [README.md](../../../README.md) for quick start instructions
- Open an issue on GitHub for specific problems or feature requests