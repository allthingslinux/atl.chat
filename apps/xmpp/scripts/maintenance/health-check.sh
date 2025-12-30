#!/bin/bash
# Health check script for Prosody XMPP Server
# Used by Docker to determine container health status

set -euo pipefail

# Configuration
PROSODY_CONFIG_FILE="${PROSODY_CONFIG_FILE:-/etc/prosody/prosody.cfg.lua}"
PROSODY_PID_FILE="${PROSODY_PID_FILE:-/var/run/prosody/prosody.pid}"
PROSODY_DOMAIN="${PROSODY_DOMAIN:-localhost}"
PROSODY_C2S_PORT="${PROSODY_C2S_PORT:-5222}"
PROSODY_HTTP_PORT="${PROSODY_HTTP_PORT:-5280}"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] HEALTH: $*" >&2
}

# Check if Prosody process is running
check_process() {
    if [[ -f "$PROSODY_PID_FILE" ]]; then
        local pid
        pid=$(cat "$PROSODY_PID_FILE" 2>/dev/null || echo "")
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi

    # Fallback: check if prosody process exists
    if pgrep -f "prosody" >/dev/null 2>&1; then
        return 0
    fi

    return 1
}

# Check if Prosody is responding on C2S port
check_c2s_port() {
    if timeout 5 bash -c "</dev/tcp/localhost/${PROSODY_C2S_PORT}" 2>/dev/null; then
        return 0
    fi
    return 1
}

# Check if HTTP services are responding
check_http_services() {
    # Check if HTTP port is open
    if ! timeout 5 bash -c "</dev/tcp/localhost/${PROSODY_HTTP_PORT}" 2>/dev/null; then
        return 1
    fi

    # Try to get a basic HTTP response
    if command -v curl >/dev/null 2>&1; then
        if curl -f -s -m 5 "http://localhost:${PROSODY_HTTP_PORT}/" >/dev/null 2>&1; then
            return 0
        fi
        # Even a 404 is fine - means HTTP is responding
        if curl -s -m 5 "http://localhost:${PROSODY_HTTP_PORT}/" 2>&1 | grep -q "404\|403\|401"; then
            return 0
        fi
    fi

    return 1
}

# Check configuration validity
check_configuration() {
    if [[ ! -f "$PROSODY_CONFIG_FILE" ]]; then
        log "Configuration file not found: $PROSODY_CONFIG_FILE"
        return 1
    fi

    # Quick syntax check
    if command -v prosodyctl >/dev/null 2>&1; then
        if ! prosodyctl check config 2>/dev/null; then
            log "Configuration validation failed"
            return 1
        fi
    fi

    return 0
}

# Main health check
main() {
    local errors=0

    # Check if process is running
    if ! check_process; then
        log "ERROR: Prosody process not running"
        ((errors++))
    fi

    # Check C2S port
    if ! check_c2s_port; then
        log "ERROR: C2S port ${PROSODY_C2S_PORT} not responding"
        ((errors++))
    fi

    # Check HTTP services
    if ! check_http_services; then
        log "ERROR: HTTP services on port ${PROSODY_HTTP_PORT} not responding"
        ((errors++))
    fi

    # Check configuration
    if ! check_configuration; then
        log "ERROR: Configuration validation failed"
        ((errors++))
    fi

    if [[ $errors -eq 0 ]]; then
        log "All health checks passed"
        exit 0
    else
        log "Health check failed with $errors error(s)"
        exit 1
    fi
}

# Run health check
main "$@"
