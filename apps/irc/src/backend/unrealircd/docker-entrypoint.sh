#!/bin/sh
set -e

# UnrealIRCd entrypoint with proper permission handling
# Handles both rootless and normal Docker setups

echo "=== UnrealIRCd Starting ==="

# Get current user ID and group ID
USER_ID=${PUID:-1000}
GROUP_ID=${PGID:-1000}

# Create directories with proper ownership
mkdir -p /home/unrealircd/unrealircd/data /home/unrealircd/unrealircd/logs /home/unrealircd/unrealircd/tmp

# Fix ownership of directories (important for rootless Docker)
chown -R "${USER_ID}:${GROUP_ID}" /home/unrealircd/unrealircd/data /home/unrealircd/unrealircd/logs /home/unrealircd/unrealircd/tmp 2> /dev/null || true

# Ensure data directory has proper permissions for control socket
chmod 755 /home/unrealircd/unrealircd/data 2> /dev/null || true

# Validate config exists
if [ ! -f "/home/unrealircd/unrealircd/conf/unrealircd.conf" ]; then
    echo "ERROR: Configuration file not found!"
    exit 1
fi

# Install third-party modules if needed (only on first run)
MODULES_INSTALLED_FLAG="/home/unrealircd/.modules_installed"
if [ ! -f "$MODULES_INSTALLED_FLAG" ] && [ -f "/usr/local/bin/install-modules.sh" ]; then
    echo "Installing third-party modules (first run)..."
    if [ "$(id -u)" = "0" ]; then
        # Running as root, switch to the specified user for module installation
        if su-exec "${USER_ID}:${GROUP_ID}" /usr/local/bin/install-modules.sh; then
            touch "$MODULES_INSTALLED_FLAG"
            chown "${USER_ID}:${GROUP_ID}" "$MODULES_INSTALLED_FLAG" 2> /dev/null || true
            echo "Third-party modules installed successfully!"
    else
            echo "Module installation failed, continuing..."
    fi
  else
        # Already running as the correct user
        if /usr/local/bin/install-modules.sh; then
            touch "$MODULES_INSTALLED_FLAG"
            echo "Third-party modules installed successfully!"
    else
            echo "Module installation failed, continuing..."
    fi
  fi
elif [ -f "$MODULES_INSTALLED_FLAG" ]; then
    echo "Third-party modules already installed (skipping)"
else
    echo "Module installation script not found, skipping..."
fi

# Start UnrealIRCd as the specified user
echo "Starting UnrealIRCd..."
if [ "$(id -u)" = "0" ]; then
    # Running as root, switch to the specified user
    exec su-exec "${USER_ID}:${GROUP_ID}" /home/unrealircd/unrealircd/bin/unrealircd -F "$@"
else
    # Already running as the correct user (Containerfile sets USER unrealircd)
    exec /home/unrealircd/unrealircd/bin/unrealircd -F "$@"
fi
