#!/bin/sh
set -e

# Atheme entrypoint with proper error handling and security

echo "=== Atheme Services Starting ==="

# Ensure we have proper permissions
if [ "$(id -u)" = "0" ]; then
    echo "ERROR: Atheme should not run as root for security reasons"
    echo "Please run with a non-root user (UID 1000 recommended)"
    exit 1
fi

# Create directories with proper ownership
mkdir -p /usr/local/atheme/data /usr/local/atheme/logs /usr/local/atheme/logs/atheme /usr/local/atheme/var

# Validate configuration exists
if [ ! -f "/usr/local/atheme/etc/atheme.conf" ]; then
    echo "ERROR: Configuration file not found at /usr/local/atheme/etc/atheme.conf"
    echo "Please ensure the configuration is properly mounted"
    exit 1
fi

# Clean up stale PID file
rm -f /usr/local/atheme/var/atheme.pid

# Validate database directory is writable
if [ ! -w "/usr/local/atheme/data" ]; then
    echo "ERROR: Data directory is not writable"
    echo "Please check volume mount permissions"
    exit 1
fi

# Validate logs directory is writable
if [ ! -w "/usr/local/atheme/logs" ]; then
    echo "ERROR: Logs directory is not writable"
    echo "Please check volume mount permissions"
    exit 1
fi

# Check if this is first run (no database exists)
if [ ! -f "/usr/local/atheme/data/services.db" ]; then
    echo "First run detected - creating initial database..."
    /usr/local/atheme/bin/atheme-services -b -c /usr/local/atheme/etc/atheme.conf -D /usr/local/atheme/data
    echo "Database created successfully"
else
    echo "Existing database found - starting with existing data"
fi

# Start Atheme services
echo "Starting Atheme services as user $(id -un) (UID: $(id -u))..."
echo "Configuration: /usr/local/atheme/etc/atheme.conf"
echo "Data directory: /usr/local/atheme/data"
echo "Logs directory: /usr/local/atheme/logs"

exec /usr/local/atheme/bin/atheme-services -n -c /usr/local/atheme/etc/atheme.conf -D /usr/local/atheme/data "$@"
