# Third-Party Modules Configuration

This directory contains the configuration for automatically installing third-party modules during the Docker build process.

## Overview

Third-party modules extend UnrealIRCd's functionality beyond the core features. These modules are maintained by the community and can be found in the official [UnrealIRCd modules repository](https://modules.unrealircd.org/).

## Configuration File: `third-party-modules.list`

The `third-party-modules.list` file contains a list of third-party modules to install during the container build process.

### Format

- One module name per line
- Lines starting with `#` are comments and are ignored
- Empty lines are ignored
- Module names should be in the format `third/module-name`

### Example

```bash
# WebIRC/WebSocket information in WHOIS
third/showwebirc

# Channel management tools
third/commandsno
third/clones

# Security enhancements
third/repeatprot
third/block_masshighlight

# Add more modules here as needed:
# third/example-module
# third/another-module
```

## How It Works

1. **Build Process**: During `docker build`, the `third-party-modules.list` file is copied into the container image
2. **Installation Script**: An installation script is created in the container image
3. **First Startup**: When the container starts for the first time, modules are downloaded and compiled
4. **Persistence**: Installed modules are stored in the container's filesystem and persist across restarts
5. **Subsequent Starts**: The flag file prevents re-installation on container restarts

## Finding Available Modules

### Online Repository
Browse available modules at: https://modules.unrealircd.org/

### Command Line
List available modules from within a running container:
```bash
docker compose exec unrealircd ./unrealircd module list
```

## Adding New Modules

1. **Edit the configuration file**:
   ```bash
   nano src/backend/unrealircd/third-party-modules.list
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
   nano src/backend/unrealircd/third-party-modules.list
   ```

2. **Comment out or delete the line**:
   ```bash
   # third/old-module-name
   ```

3. **Rebuild the container**:
   ```bash
   make rebuild
   ```

## Module Information

Get detailed information about a specific module:
```bash
docker compose exec unrealircd ./unrealircd module info third/module-name
```


## Currently Installed Modules

- **third/showwebirc**: Adds WebIRC and WebSocket information to WHOIS queries

## System Files

- **`third-party-modules.list`**: Configuration file listing modules to install
- **`/usr/local/bin/install-modules.sh`**: Generated installation script
- **`/home/unrealircd/.modules_installed`**: Flag file created after successful installation

## Installation Process

The third-party modules are automatically installed when the container starts for the first time:

1. **Container Build**: The `third-party-modules.list` file is copied into the container
2. **First Startup**: The entrypoint script detects this is the first run and installs modules
3. **Flag File**: A `.modules_installed` flag is created to prevent re-installation
4. **Subsequent Starts**: The flag file prevents redundant installations

## Manual Installation

If you need to install additional modules after the container is running:

```bash
# Enter the container
docker compose exec unrealircd sh

# Install a module manually
cd /home/unrealircd/unrealircd
./unrealircd module install third/module-name

# Rehash to load the module
./bin/unrealircdctl rehash
```

## Troubleshooting

### Module Installation Fails
- Check that the module name is correct and exists in the repository
- Verify network connectivity for downloading modules
- Check UnrealIRCd logs for detailed error messages

### Module Not Loading After Installation
- Ensure you ran `./bin/unrealircdctl rehash` after installation
- Check that the module file exists in `/home/unrealircd/unrealircd/modules/third/`
- Verify the module is listed in your `unrealircd.conf`

### Permission Issues
- The installation script automatically handles permissions
- If issues persist, check the user ID settings in your environment

### Force Reinstallation
If you need to force reinstallation of modules (e.g., after changing the list):
```bash
# Remove the installation flag
docker compose exec unrealircd rm -f /home/unrealircd/.modules_installed

# Restart the container
docker compose restart unrealircd
```

## Advanced Configuration

### Module Dependencies
Some modules may require additional system packages. If a module fails to compile, you may need to add dependencies to the Containerfile.

### Custom Module Sources
If you need modules from custom repositories, you can modify the `modules.sources.list` file in the container.

### Module Updates
To update installed modules:
```bash
docker compose exec unrealircd ./unrealircd module upgrade
```

## Best Practices

1. **Test modules** in a development environment before production use
2. **Keep the list updated** with only needed modules for security
3. **Document custom modules** with comments in the configuration file
4. **Regularly check** for module updates using `./unrealircd module upgrade`

## Security Considerations

- Third-party modules are not officially supported by the UnrealIRCd team
- Review module source code if security is a concern
- Only install modules from trusted sources
- Regularly update modules for security patches
