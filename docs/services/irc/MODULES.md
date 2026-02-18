# UnrealIRCd Modules

This guide covers the module system in UnrealIRCd for IRC.atl.chat, focusing on third-party module management and configuration.

## Overview

### Module Architecture

UnrealIRCd uses a modular architecture where functionality is provided by loadable modules:

- **Core Modules**: Built-in functionality (user modes, channel modes, etc.)
- **Third-Party Modules**: Community-developed extensions
- **Module Management**: Automated installation and configuration via Docker

### Module Categories

```
Modules/
├── usermodes/          # User mode implementations
├── chanmodes/          # Channel mode implementations
├── commands/           # IRC command extensions
├── extensions/         # Protocol extensions (IRCv3, etc.)
├── third/             # Third-party modules
├── crypto/            # Cryptographic functions
└── backend/           # Database backends
```

## Third-Party Modules Configuration

### Automatic Installation

Third-party modules are automatically installed during container build using the `third-party-modules.list` file:

```bash
# Edit the modules list
vim apps/unrealircd/third-party-modules.list

# Add modules (one per line)
third/showwebirc
third/geoip

# Rebuild container to install modules
make rebuild
```

### Module List File Format

```bash
# Comments start with #
# Empty lines are ignored
# One module per line

# WebIRC/WebSocket information in WHOIS
third/showwebirc

# Add more modules here as needed:
# third/example-module
```

### Installation Process

1. **Build Time**: Modules listed in `third-party-modules.list` are installed during container build
2. **First Run**: Installation script runs automatically on first container startup
3. **Persistence**: Installed modules persist across container restarts
4. **Flag File**: `.modules_installed` prevents re-installation

## Module Management Commands

### Using Make Commands
```bash
# List available third-party modules
make modules-list

# Show installed modules
make modules-installed
```

### Using Management Scripts
```bash
# List available modules
docker compose exec atl-irc-server manage-modules.sh list

# Show module information
docker compose exec atl-irc-server manage-modules.sh info webpanel

# Install a module
docker compose exec atl-irc-server manage-modules.sh install webpanel

# Uninstall a module
docker compose exec atl-irc-server manage-modules.sh uninstall webpanel

# Show installed modules
docker compose exec atl-irc-server manage-modules.sh installed
```

### Configuration Management
```bash
# Add module to configuration
docker compose exec atl-irc-server module-config.sh add webpanel

# Remove module from configuration
docker compose exec atl-irc-server module-config.sh remove webpanel

# List loaded modules in config
docker compose exec atl-irc-server module-config.sh list
```

### Runtime Module Management
```bash
# List loaded modules
MODULE LIST

# Load module at runtime
MODULE LOAD mymodule

# Unload module
MODULE UNLOAD mymodule
```

## Module Configuration

### Configuration Files

#### modules.default.conf
Contains core modules required for basic functionality:

```c
// Core modules - DO NOT REMOVE
loadmodule "cloak_sha256";
loadmodule "usermodes/secureonlymsg";
loadmodule "chanmodes/ban";
loadmodule "chanmodes/inviteonly";

// Standard extensions
loadmodule "extensions/ircv3";
loadmodule "extensions/sasl";
```

#### modules.custom.conf
Site-specific modules:

```c
// Third-party modules
loadmodule "third/showwebirc";
loadmodule "third/geoip";

// Custom modules
// loadmodule "mymodule";
```

#### modules.optional.conf
Optional features:

```c
// Load as needed
// loadmodule "chanmodes/auditorium";
// loadmodule "usermodes/censor";
```

## Currently Installed Modules

- **third/showwebirc**: Adds WebIRC and WebSocket information to WHOIS queries

## Troubleshooting

### Common Issues

#### Module Not Loading
```bash
# Check module file exists
docker compose exec atl-irc-server ls -la /home/unrealircd/unrealircd/modules/third/

# Check logs for errors
make logs-ircd | grep -i module
```

#### Configuration Errors
```bash
# Validate configuration
docker compose exec atl-irc-server unrealircd -c /home/unrealircd/unrealircd/config/unrealircd.conf

# Check syntax errors
make logs-ircd | grep -i error
```

#### Force Reinstallation
If you need to force reinstallation of modules:

```bash
# Remove the installation flag
docker compose exec atl-irc-server rm -f /home/unrealircd/.modules_installed

# Restart the container
docker compose restart atl-irc-server
```

### Debug Information

```bash
# Check module status
docker compose exec atl-irc-server unrealircdctl module list

# Enable debug logging
# Add to unrealircd.conf:
# set { log-level debug; };
```

## Finding Available Modules

### Online Repository
Browse available modules at: https://modules.unrealircd.org/

### Command Line
List available modules from within a running container:
```bash
docker compose exec atl-irc-server ./unrealircd module list
```

## Adding New Modules

1. **Edit the configuration file**:
   ```bash
   nano apps/unrealircd/third-party-modules.list
   ```

2. **Add the module name** (one per line):
   ```bash
   third/new-module-name
   ```

3. **Rebuild the container**:
   ```bash
   make rebuild
   ```

## Removing Modules

1. **Remove from the configuration file**:
   ```bash
   nano apps/unrealircd/third-party-modules.list
   ```

2. **Comment out or delete the line**:
   ```bash
   # third/old-module-name
   ```

3. **Rebuild the container**:
   ```bash
   make rebuild
   ```

## Manual Installation

If you need to install additional modules after the container is running:

```bash
# Enter the container
docker compose exec atl-irc-server sh

# Install a module manually
cd /home/unrealircd/unrealircd
./unrealircd module install third/module-name

# Rehash to load the module
./bin/unrealircdctl rehash
```

## Security Considerations

- Third-party modules are not officially supported by the UnrealIRCd team
- Review module source code if security is a concern
- Only install modules from trusted sources
- Regularly update modules for security patches

## Related Documentation

- [UNREALIRCD.md](UNREALIRCD.md) - Main server configuration
- [CONFIG.md](CONFIG.md) - Configuration management
- [DOCKER.md](DOCKER.md) - Container setup
- [UnrealIRCd Module API](https://www.unrealircd.org/docs/module_api) - Official API docs
- [Third-Party Modules](https://modules.unrealircd.org/) - Module repository