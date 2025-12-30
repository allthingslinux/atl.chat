#!/bin/bash

# Production Secrets Setup Script
# This script helps set up sensitive environment variables for production
# Run this on your production server after deploying the code

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
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

# Check if we're running as root (for Docker)
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        log_warn "Running as root - ensure Docker containers have proper user mapping"
    fi
}

# Generate secure password
generate_password() {
    local length="${1:-32}"
    openssl rand -base64 "$length" | tr -d '\n' | tr -d '/' | cut -c1-"$length"
}

# Setup database password
setup_database_password() {
    log_info "Setting up database password..."

    if [[ -z "${PROSODY_DB_PASSWORD:-}" ]]; then
        local db_password
        db_password=$(generate_password 32)
        echo "PROSODY_DB_PASSWORD=$db_password" >> .env.production.local
        log_success "Generated database password"
    else
        log_info "Database password already set"
    fi

    # Also set PostgreSQL password for Docker
    if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
        local pg_password
        pg_password=$(generate_password 32)
        echo "POSTGRES_PASSWORD=$pg_password" >> .env.production.local
        echo "ADMINER_DEFAULT_PASSWORD=$pg_password" >> .env.production.local
        log_success "Generated PostgreSQL passwords"
    fi
}

# Setup admin password
setup_admin_password() {
    log_info "Setting up admin password..."

    if [[ -z "${PROSODY_ADMIN_PASSWORD:-}" ]]; then
        local admin_password
        admin_password=$(generate_password 24)
        echo "PROSODY_ADMIN_PASSWORD=$admin_password" >> .env.production.local
        log_success "Generated admin password"
        log_warn "Save this password securely: $admin_password"
    else
        log_info "Admin password already set"
    fi
}

# Setup TURN secret
setup_turn_secret() {
    log_info "Setting up TURN secret..."

    if [[ -z "${TURN_SECRET:-}" ]]; then
        local turn_secret
        turn_secret=$(generate_password 40)
        echo "TURN_SECRET=$turn_secret" >> .env.production.local
        log_success "Generated TURN secret"
    else
        log_info "TURN secret already set"
    fi
}

# Setup Cloudflare credentials for DNS-01 challenge
setup_cloudflare_credentials() {
    log_info "Setting up Cloudflare credentials for SSL certificates..."

    local cf_email cf_api_key

    echo "Please enter your Cloudflare email:"
    read -r cf_email

    echo "Please enter your Cloudflare API key (keep this secret):"
    read -r -s cf_api_key
    echo

    if [[ -n "$cf_email" && -n "$cf_api_key" ]]; then
        echo "CLOUDFLARE_EMAIL=$cf_email" >> .env.production.local
        echo "CLOUDFLARE_API_KEY=$cf_api_key" >> .env.production.local

        # Create Cloudflare credentials file for Certbot
        mkdir -p .runtime
        cat > .runtime/cloudflare-credentials.ini << EOF
# Cloudflare API credentials for DNS-01 challenge
dns_cloudflare_email = $cf_email
dns_cloudflare_api_key = $cf_api_key
EOF
        chmod 600 .runtime/cloudflare-credentials.ini
        log_success "Cloudflare credentials configured"
    else
        log_warn "Cloudflare credentials not provided - SSL certificates will need manual configuration"
    fi
}

# Create .env.production.local if it doesn't exist
create_local_env_file() {
    if [[ ! -f .env.production.local ]]; then
        touch .env.production.local
        chmod 600 .env.production.local
        log_success "Created .env.production.local for secrets"
    fi
}

# Main setup function
main() {
    echo "=========================================="
    echo "XMPP Production Secrets Setup"
    echo "=========================================="
    echo

    check_permissions
    create_local_env_file

    echo "This script will set up sensitive environment variables for production."
    echo "These will be stored in .env.production.local (not committed to git)"
    echo

    setup_database_password
    setup_admin_password
    setup_turn_secret
    setup_cloudflare_credentials

    echo
    log_success "Production secrets setup complete!"
    echo
    echo "Next steps:"
    echo "1. Review the generated secrets in .env.production.local"
    echo "2. Ensure .env.production.local is in your .gitignore"
    echo "3. Run 'docker compose --env-file .env.production.local up -d'"
    echo "4. Set up SSL certificates: 'docker compose --env-file .env.production.local run --rm xmpp-certbot'"
    echo
    log_warn "Remember to backup your secrets securely!"
}

# Run main function
main "$@"
