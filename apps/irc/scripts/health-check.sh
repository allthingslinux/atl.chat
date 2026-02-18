#!/bin/bash

# Health check script for UnrealIRCd (host-side)
# Checks if UnrealIRCd is responding on the IRC port

set -e

# Configuration
IRC_PORT=${IRC_PORT:-6697}

# Function to check port
check_port() {
    local port=$1

    if command -v nc > /dev/null 2>&1; then
        nc -z localhost "$port" 2> /dev/null
        return $?
    elif command -v netcat > /dev/null 2>&1; then
        netcat -z localhost "$port" 2> /dev/null
        return $?
    else
        echo "ERROR: Neither 'nc' nor 'netcat' available for health check"
        return 1
    fi
}

# Main health check
echo "Checking UnrealIRCd health on port $IRC_PORT..."

if check_port "$IRC_PORT"; then
    echo "SUCCESS: UnrealIRCd is responding on port $IRC_PORT"
    exit 0
else
    echo "FAILED: UnrealIRCd is not responding on port $IRC_PORT"
    exit 1
fi
