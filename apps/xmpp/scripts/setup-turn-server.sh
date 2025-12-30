#!/bin/bash
# TURN Server Configuration Setup Script
# This script sets up the TURN server configuration with environment variables

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TURN_CONFIG_FILE="${PROJECT_DIR}/.runtime/turn/turnserver.conf"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Load environment variables
load_env() {
    if [[ -f "${PROJECT_DIR}/.env" ]]; then
        # shellcheck source=/dev/null
        source "${PROJECT_DIR}/.env"
    fi
}

# Update TURN configuration with environment variables
update_turn_config() {
    log_info "Updating TURN server configuration..."

    # Create backup
    if [[ -f "$TURN_CONFIG_FILE" ]]; then
        cp "$TURN_CONFIG_FILE" "${TURN_CONFIG_FILE}.backup"
    fi

    # Update configuration values
    sed -i "s/vEIheW+T+MiuulmzX69ck7UJ3ZxuhZLZiykq9XvBU98=/${TURN_SECRET:-vEIheW+T+MiuulmzX69ck7UJ3ZxuhZLZiykq9XvBU98=}/g" "$TURN_CONFIG_FILE"
    sed -i "s/realm=atl.chat/realm=${TURN_REALM:-atl.chat}/g" "$TURN_CONFIG_FILE"
    sed -i "s/server-name=turn.atl.chat/server-name=${TURN_DOMAIN:-turn.atl.chat}/g" "$TURN_CONFIG_FILE"

    log_success "TURN server configuration updated"
}

# Validate TURN configuration
validate_turn_config() {
    log_info "Validating TURN server configuration..."

    if [[ ! -f "$TURN_CONFIG_FILE" ]]; then
        log_error "TURN configuration file not found: $TURN_CONFIG_FILE"
        return 1
    fi

    # Check for required configuration
    if ! grep -q "use-auth-secret" "$TURN_CONFIG_FILE"; then
        log_warn "use-auth-secret not found in TURN configuration"
    fi

    if ! grep -q "fingerprint" "$TURN_CONFIG_FILE"; then
        log_warn "fingerprint not found in TURN configuration"
    fi

    log_success "TURN server configuration is valid"
}

# Setup TURN certificates
setup_turn_certificates() {
    log_info "Setting up TURN server certificates..."

    # Ensure certificate directory exists
    mkdir -p "${PROJECT_DIR}/.runtime/certs"

    # Copy certificates from Let's Encrypt if available
    if [[ -f "${PROJECT_DIR}/.runtime/certs/live/${PROSODY_DOMAIN:-example.com}/fullchain.pem" ]]; then
        cp "${PROJECT_DIR}/.runtime/certs/live/${PROSODY_DOMAIN:-example.com}/fullchain.pem" "${PROJECT_DIR}/.runtime/certs/cert.pem"
        cp "${PROJECT_DIR}/.runtime/certs/live/${PROSODY_DOMAIN:-example.com}/privkey.pem" "${PROJECT_DIR}/.runtime/certs/privkey.pem"
        log_success "TURN certificates copied from Let's Encrypt"
    else
        log_warn "Let's Encrypt certificates not found. Using self-signed certificates for TURN server"
        # Generate self-signed certificate for TURN server
        openssl req -x509 -newkey rsa:4096 -keyout "${PROJECT_DIR}/.runtime/certs/privkey.pem" -out "${PROJECT_DIR}/.runtime/certs/cert.pem" -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=${TURN_DOMAIN:-turn.atl.chat}"
        log_success "Self-signed certificate generated for TURN server"
    fi

    # Set proper permissions
    chmod 644 "${PROJECT_DIR}/.runtime/certs/cert.pem"
    chmod 600 "${PROJECT_DIR}/.runtime/certs/privkey.pem"
}

# Main function
main() {
    echo "TURN Server Configuration Setup"
    echo "==============================="
    echo ""

    # Load environment variables
    load_env

    # Update TURN configuration
    update_turn_config

    # Validate configuration
    validate_turn_config

    # Setup certificates
    setup_turn_certificates

    echo ""
    log_success "TURN server setup completed successfully!"
    echo ""
    echo "TURN Server Configuration:"
    echo "  Domain: ${TURN_DOMAIN:-turn.atl.chat}"
    echo "  Realm: ${TURN_REALM:-atl.chat}"
    echo "  Port: ${TURN_PORT:-3478}"
    echo "  TLS Port: ${TURNS_PORT:-5349}"
    echo "  Relay Ports: ${TURN_MIN_PORT:-50000}-${TURN_MAX_PORT:-50100}"
    echo ""
    echo "To start the TURN server:"
    echo "  docker compose up xmpp-coturn"
}

# Run main function
main "$@"
