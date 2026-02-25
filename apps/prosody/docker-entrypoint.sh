#!/bin/bash
set -euo pipefail

# Prosody XMPP Server Docker entrypoint
# Handles env validation, cert setup, DB wait, and starts Prosody in foreground

# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

readonly PROSODY_USER="prosody"
readonly PROSODY_CONFIG_DIR="/etc/prosody"
readonly PROSODY_DATA_DIR="/var/lib/prosody"
readonly PROSODY_LOG_DIR="/var/log/prosody"
readonly PROSODY_CERT_DIR="/etc/prosody/certs"
readonly PROSODY_UPLOAD_DIR="/var/lib/prosody/uploads"
readonly PROSODY_CONFIG_FILE="${PROSODY_CONFIG_DIR}/prosody.cfg.lua"
readonly PROSODY_PID_FILE="/var/run/prosody/prosody.pid"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1" >&2
}

log_debug() {
    if [[ "${PROSODY_LOG_LEVEL:-info}" == "debug" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1" >&2
    fi
}

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

validate_environment() {
    log_info "Validating environment configuration..."

    # Validate required domain
    if [[ -z "${PROSODY_DOMAIN:-}" ]]; then
        log_error "PROSODY_DOMAIN is required but not set"
        exit 1
    fi

    # Validate domain format
    if [[ ! "${PROSODY_DOMAIN}" =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$ ]]; then
        log_error "Invalid domain format: ${PROSODY_DOMAIN}"
        exit 1
    fi

    # Set default admin if not provided
    if [[ -z "${PROSODY_ADMIN_JID:-}" ]]; then
        export PROSODY_ADMIN_JID="admin@${PROSODY_DOMAIN}"
        log_info "Using default admin: ${PROSODY_ADMIN_JID}"
    fi

    # Validate database configuration for SQL storage
    if [[ "${PROSODY_STORAGE:-sql}" == "sql" ]]; then
        local required_vars=(
            "PROSODY_DB_DRIVER"
            "PROSODY_DB_NAME"
            "PROSODY_DB_USER"
            "PROSODY_DB_PASSWORD"
            "PROSODY_DB_HOST"
        )

        for var in "${required_vars[@]}"; do
            if [[ -z "${!var:-}" ]]; then
                log_error "Database variable ${var} is required for SQL storage"
                exit 1
            fi
        done
    fi

    log_info "Environment validation complete"
}

# ============================================================================
# SETUP FUNCTIONS
# ============================================================================

setup_directories() {
    log_info "Setting up directories..."

    local dirs=(
        "$PROSODY_DATA_DIR"
        "$PROSODY_LOG_DIR"
        "$PROSODY_CERT_DIR"
        "$PROSODY_UPLOAD_DIR"
        "$(dirname "$PROSODY_PID_FILE")"
    )

    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            log_debug "Creating directory: $dir"
            mkdir -p "$dir"
        fi

        # Ensure proper ownership (only if running as root)
        if [[ $EUID -eq 0 ]]; then
            chown -R "$PROSODY_USER:$PROSODY_USER" "$dir" 2> /dev/null || true
        fi
    done

    # Critical: bind-mounted data dir (e.g. data/xmpp/data) may have host ownership;
    # Prosody needs write access for SQLite (MAM, PEP, etc.)
    if [[ $EUID -eq 0 ]] && [[ -d "${PROSODY_DATA_DIR}/data" ]]; then
        if ! chown -R "$PROSODY_USER:$PROSODY_USER" "${PROSODY_DATA_DIR}/data"; then
            log_warn "chown of data dir failed - SQL/MAM may be read-only (check volume permissions)"
        fi
    fi

    log_info "Directory setup complete"
}

setup_certificates() {
    log_info "Setting up SSL certificates..."

    # Use live/<domain>/ layout (matches init.sh and Let's Encrypt)
    local live_dir="${PROSODY_CERT_DIR}/live/${PROSODY_DOMAIN}"
    local cert_file="${live_dir}/fullchain.pem"
    local key_file="${live_dir}/privkey.pem"

    if [[ -f "$cert_file" && -f "$key_file" ]]; then
        log_info "Certificates found for ${PROSODY_DOMAIN}"
        if [[ $EUID -eq 0 ]]; then
            chown -R "$PROSODY_USER:$PROSODY_USER" "$live_dir" || true
        fi
        chmod 644 "$cert_file" 2> /dev/null || true
        chmod 600 "$key_file" 2> /dev/null || true
        return 0
    fi

    # Fallback: check legacy layout (xmpp.localhost.crt / .key) for backwards compat
    local legacy_cert="${PROSODY_CERT_DIR}/${PROSODY_DOMAIN}.crt"
    local legacy_key="${PROSODY_CERT_DIR}/${PROSODY_DOMAIN}.key"
    if [[ -f "$legacy_cert" && -f "$legacy_key" ]]; then
        log_info "Legacy certificates found, copying to live/${PROSODY_DOMAIN}/"
        mkdir -p "$live_dir"
        cp "$legacy_cert" "$cert_file"
        cp "$legacy_key" "$key_file"
        if [[ $EUID -eq 0 ]]; then
            chown -R "$PROSODY_USER:$PROSODY_USER" "$live_dir" || true
        fi
        chmod 644 "$cert_file"
        chmod 600 "$key_file"
        return 0
    fi

    # Generate self-signed certificate for development/testing
    log_warn "No certificates found, generating self-signed certificate for ${PROSODY_DOMAIN}"
    log_warn "This is suitable for development only - use proper certificates in production"

    mkdir -p "$live_dir"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$key_file" \
        -out "$cert_file" \
        -subj "/CN=${PROSODY_DOMAIN}" \
        -addext "subjectAltName=DNS:${PROSODY_DOMAIN},DNS:*.${PROSODY_DOMAIN},DNS:muc.${PROSODY_DOMAIN},DNS:upload.${PROSODY_DOMAIN},DNS:proxy.${PROSODY_DOMAIN},DNS:pubsub.${PROSODY_DOMAIN},DNS:bridge.${PROSODY_DOMAIN},DNS:localhost,IP:127.0.0.1" 2>/dev/null

    if [[ $EUID -eq 0 ]]; then
        chown -R "$PROSODY_USER:$PROSODY_USER" "$live_dir" || true
    fi
    chmod 644 "$cert_file"
    chmod 600 "$key_file"

    log_info "Self-signed certificate generated successfully"
}

wait_for_database() {
    if [[ "${PROSODY_STORAGE:-sql}" != "sql" ]]; then
        log_debug "Not using SQL storage, skipping database wait"
        return 0
    fi

    local host="${PROSODY_DB_HOST}"
    local port="${PROSODY_DB_PORT:-5432}"
    local max_attempts=30
    local attempt=1

    log_info "Waiting for database connection to ${host}:${port}..."

    while [[ $attempt -le $max_attempts ]]; do
        if timeout 5 bash -c "</dev/tcp/${host}/${port}" 2> /dev/null; then
            log_info "Database connection established"
            return 0
        fi

        log_debug "Database not ready, attempt ${attempt}/${max_attempts}"
        sleep 2
        ((attempt++))
    done

    log_error "Database connection timeout after ${max_attempts} attempts"
    exit 1
}

validate_configuration() {
    log_info "Validating Prosody configuration..."

    # Check if config file exists
    if [[ ! -f "$PROSODY_CONFIG_FILE" ]]; then
        log_error "Configuration file not found: $PROSODY_CONFIG_FILE"
        exit 1
    fi

    # Validate configuration using prosodyctl (allow warnings in development)
    log_info "Validating Prosody configuration..."
    if ! prosodyctl check config; then
        log_error "Prosody configuration validation failed"
        log_error "Please check your configuration file: $PROSODY_CONFIG_FILE"
        if [[ "${PROSODY_DEVELOPMENT_MODE:-false}" != "true" ]]; then
            exit 1
        else
            log_warn "Development mode: continuing despite configuration warnings"
        fi
    fi

    log_info "Configuration validation successful"
}

setup_community_modules() {
    log_info "Setting up community modules..."

    # Check if community modules source exists
    local source_dir="/usr/local/lib/prosody/prosody-modules"
    if [[ ! -d "$source_dir" ]]; then
        log_warn "Community modules repository not found at $source_dir"
        log_warn "Modules will need to be installed manually or via prosodyctl"
        return 0
    fi

    # Check if modules are available from enabled directory
    local enabled_dir="/usr/local/lib/prosody/prosody-modules-enabled"
    if [[ ! -d "$enabled_dir" ]]; then
        log_warn "Enabled community modules directory not found at $enabled_dir"
        return 0
    else
        log_info "Community modules found in $enabled_dir"
        local module_count
        module_count=$(find "$enabled_dir" -maxdepth 1 -type l 2> /dev/null | wc -l)
        log_info "Enabled modules: $module_count"
    fi

    # Ensure proper ownership (only if running as root)
    if [[ $EUID -eq 0 ]]; then
        chown -R "$PROSODY_USER:$PROSODY_USER" "$source_dir" "$enabled_dir" 2> /dev/null || true
    fi
}

# ============================================================================
# SIGNAL HANDLERS
# ============================================================================

# shellcheck disable=SC2317,SC2329  # Function is called by signal handlers via trap
cleanup() {
    log_info "Received shutdown signal, stopping Prosody..."

    if [[ -n "${PROSODY_PID:-}" ]] && kill -0 "$PROSODY_PID" 2> /dev/null; then
        # Send SIGTERM for graceful shutdown
        kill -TERM "$PROSODY_PID" 2> /dev/null || true

        # Wait for graceful shutdown (max 30 seconds)
        local timeout=30
        while kill -0 "$PROSODY_PID" 2> /dev/null && [[ $timeout -gt 0 ]]; do
            sleep 1
            ((timeout--))
        done

        # Force kill if still running
        if kill -0 "$PROSODY_PID" 2> /dev/null; then
            log_warn "Prosody did not shut down gracefully, forcing termination"
            kill -KILL "$PROSODY_PID" 2> /dev/null || true
        fi
    fi

    log_info "Prosody shutdown complete"
    exit 0
}

# Setup signal handlers
trap cleanup SIGTERM SIGINT SIGQUIT

# ============================================================================
# MAIN FUNCTION
# ============================================================================

main() {
    log_info "Starting Professional Prosody XMPP Server..."

    # Display version information
    local prosody_version
    prosody_version=$(prosody --version 2> /dev/null | head -n1 || echo "Unknown")
    log_info "Prosody version: $prosody_version"

    # Prefer mounted config if present
    if [[ -f "/etc/prosody/config/prosody.cfg.lua" ]]; then
        log_info "Detected mounted config at /etc/prosody/config/prosody.cfg.lua; syncing to ${PROSODY_CONFIG_FILE}"
        cp -f "/etc/prosody/config/prosody.cfg.lua" "${PROSODY_CONFIG_FILE}"
        chown root:prosody "${PROSODY_CONFIG_FILE}" 2> /dev/null || true
        chmod 640 "${PROSODY_CONFIG_FILE}" 2> /dev/null || true
    fi

    # If a mounted conf.d exists, sync it into /etc/prosody/conf.d so Include() works
    if [[ -d "/etc/prosody/config/conf.d" ]]; then
        log_info "Detected mounted conf.d include directory; syncing to /etc/prosody/conf.d"
        mkdir -p "/etc/prosody/conf.d"
        rsync -a --delete "/etc/prosody/config/conf.d/" "/etc/prosody/conf.d/"
        chown -R root:prosody "/etc/prosody/conf.d" 2> /dev/null || true
        find /etc/prosody/conf.d -type f -name '*.lua' -exec chmod 640 {} + 2> /dev/null || true
    fi

    # Environment and setup
    validate_environment
    setup_directories
    setup_certificates
    wait_for_database
    validate_configuration
    setup_community_modules

    # Display configuration summary
    log_info "Configuration summary:"
    log_info "  Domain: ${PROSODY_DOMAIN}"
    log_info "  Admins: ${PROSODY_ADMIN_JID}"
    log_info "  Storage: ${PROSODY_STORAGE:-sql}"
    log_info "  Log level: ${PROSODY_LOG_LEVEL:-info}"
    log_info "  Allow registration: ${PROSODY_ALLOW_REGISTRATION:-false} (Portal provisions via mod_http_admin_api when false)"

    if [[ "${PROSODY_STORAGE:-sql}" == "sql" ]]; then
        log_info "  Database: ${PROSODY_DB_DRIVER} on ${PROSODY_DB_HOST}:${PROSODY_DB_PORT:-5432}"
    fi

    # Start Prosody
    log_info "Starting Prosody XMPP server..."

    # Switch to prosody user and start in foreground
    exec gosu "$PROSODY_USER" prosody \
        --config="$PROSODY_CONFIG_FILE" \
        --foreground
}

# ============================================================================
# SCRIPT EXECUTION
# ============================================================================

# Ensure we're running as root initially (for setup)
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root for initial setup"
    exit 1
fi

# Execute main function
main "$@"
