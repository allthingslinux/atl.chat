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
if [ ! -f "/home/unrealircd/unrealircd/config/unrealircd.conf" ]; then
    echo "ERROR: Configuration file not found!"
    exit 1
fi

# Ownership and permissions are handled by Containerfile and user switching

# Handle commands
case "$1" in
    start)
        shift
        echo "Starting UnrealIRCd in foreground..."
        if [ "$(id -u)" = "0" ]; then
            exec su-exec "${USER_ID}:${GROUP_ID}" /home/unrealircd/unrealircd/bin/unrealircd -F "$@"
        else
            exec /home/unrealircd/unrealircd/bin/unrealircd -F "$@"
        fi
        ;;
    *)
        echo "Running command: $1"
        if [ "$(id -u)" = "0" ]; then
            exec su-exec "${USER_ID}:${GROUP_ID}" /home/unrealircd/unrealircd/unrealircd "$@"
        else
            exec /home/unrealircd/unrealircd/unrealircd "$@"
        fi
        ;;
esac
