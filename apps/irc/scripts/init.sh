#!/bin/bash
# shellcheck shell=bash

# IRC Infrastructure Initialization Script
# Creates required directory structure on host system

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS_IRC_ROOT="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$(dirname "$APPS_IRC_ROOT")")"

# Load environment variables from .env file if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a # automatically export all variables

    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env"

    set +a # stop automatically exporting
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to create directory structure
create_directories() {
    log_info "Creating required directory structure..."

    # Data directories
    local data_dirs=(
        "$PROJECT_ROOT/data/unrealircd"
        "$PROJECT_ROOT/data/atheme"
    )

    # Log directories
    local log_dirs=(
        "$PROJECT_ROOT/logs/unrealircd"
        "$PROJECT_ROOT/logs/atheme"
    )

    # SSL directories
    local ssl_dirs=(
        "$APPS_IRC_ROOT/services/unrealircd/config/tls"
    )

    # Create all directories
    for dir in "${data_dirs[@]}" "${log_dirs[@]}" "${ssl_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "Created directory: $dir"
    else
            log_info "Directory already exists: $dir"
    fi
  done

    log_success "Directory structure created successfully"
}

# Function to set proper permissions
set_permissions() {
    log_info "Setting proper permissions..."

    # Get current user ID and group ID
    local current_uid
    local current_gid
    # Use actual user ID instead of hardcoded values
    current_uid=$(id -u)
    current_gid=$(id -g)

    # Use same UID for all services to avoid permission issues
    local atheme_uid=$current_uid
    local atheme_gid=$current_gid

    log_info "Current user: $current_uid:$current_gid"

    # Set ownership for data directories (if they exist)
    if [ -d "$PROJECT_ROOT/data" ]; then
        sudo chown -R "$current_uid:$current_gid" "$PROJECT_ROOT/data"
        # Ensure directories are writable by owner (critical for socket creation)
        find "$PROJECT_ROOT/data" -type d -exec chmod 755 {} \;
        log_info "Set ownership for data directory"
  fi

    # Ensure UnrealIRCd data directory specifically has correct permissions
    if [ -d "$PROJECT_ROOT/data/unrealircd" ]; then
        sudo chown -R "$current_uid:$current_gid" "$PROJECT_ROOT/data/unrealircd"
        chmod 755 "$PROJECT_ROOT/data/unrealircd"
        log_info "Set permissions for UnrealIRCd data directory"
  fi

    # Set ownership for Atheme data directory with correct UID
    if [ -d "$PROJECT_ROOT/data/atheme" ]; then
        sudo chown -R "$atheme_uid:$atheme_gid" "$PROJECT_ROOT/data/atheme"
        chmod 755 "$PROJECT_ROOT/data/atheme"
        log_info "Set permissions for Atheme data directory"
  fi

    # Set ownership for log directories (if they exist)
    if [ -d "$PROJECT_ROOT/logs" ]; then
        sudo chown -R "$current_uid:$current_gid" "$PROJECT_ROOT/logs"
        # Ensure directories are writable by owner
        find "$PROJECT_ROOT/logs" -type d -exec chmod 755 {} \;
        log_info "Set ownership for logs directory"
  fi

    # Set ownership for Atheme logs with correct UID
    if [ -d "$PROJECT_ROOT/logs/atheme" ]; then
        sudo chown -R "$atheme_uid:$atheme_gid" "$PROJECT_ROOT/logs/atheme"
        chmod 755 "$PROJECT_ROOT/logs/atheme"
        log_info "Set permissions for Atheme logs directory"
  fi

    # Set permissions for SSL certificates
    if [ ! -d "$APPS_IRC_ROOT/services/unrealircd/config/tls" ]; then
        sudo mkdir -p "$APPS_IRC_ROOT/services/unrealircd/config/tls"
    fi
    sudo chown "$current_uid:$current_gid" "$APPS_IRC_ROOT/services/unrealircd/config/tls" 2> /dev/null || true
    chmod 755 "$APPS_IRC_ROOT/services/unrealircd/config/tls" || sudo chmod 755 "$APPS_IRC_ROOT/services/unrealircd/config/tls" || log_warning "Could not set permissions for SSL directory"
    log_info "Set permissions for SSL directory"

    # Make sure data directories are writable
    find "$PROJECT_ROOT/data" -type d -exec chmod 755 {} \; 2> /dev/null || true
    find "$PROJECT_ROOT/atheme" -type d -exec chmod 755 {} \; 2> /dev/null || true
    find "$PROJECT_ROOT/logs" -type d -exec chmod 755 {} \; 2> /dev/null || true

    log_success "Permissions set successfully"
}

# Function to set up CA certificate bundle
setup_ca_bundle() {
    log_info "Setting up CA certificate bundle..."

    local ca_template_dir="$PROJECT_ROOT/docs/examples/unrealircd/tls"
    local ca_runtime_dir="$APPS_IRC_ROOT/services/unrealircd/config/tls"
    local ca_bundle_file="curl-ca-bundle.crt"

    # Ensure runtime directory exists
    if [ ! -d "$ca_runtime_dir" ]; then
        mkdir -p "$ca_runtime_dir"
        log_info "Created TLS runtime directory: $ca_runtime_dir"
  fi

    # Ensure template directory exists
    if [ ! -d "$ca_template_dir" ]; then
        mkdir -p "$ca_template_dir"
        log_info "Created TLS template directory: $ca_template_dir"
  fi

    # Check if system CA bundle exists
    local system_ca_bundle=""
    if [ -f "/etc/ca-certificates/extracted/tls-ca-bundle.pem" ]; then
        system_ca_bundle="/etc/ca-certificates/extracted/tls-ca-bundle.pem"
  elif   [ -f "/etc/ssl/certs/ca-certificates.crt" ]; then
        system_ca_bundle="/etc/ssl/certs/ca-certificates.crt"
  fi

    if [ -n "$system_ca_bundle" ]; then
        # Create template if it doesn't exist
        if [ ! -f "$ca_template_dir/$ca_bundle_file" ]; then
            if cp "$system_ca_bundle" "$ca_template_dir/$ca_bundle_file"; then
                log_success "Created CA certificate bundle template"
      else
                log_warning "Could not create CA certificate bundle template"
                return 1
      fi
    fi

        # Copy to runtime directory if it doesn't exist
        if [ ! -f "$ca_runtime_dir/$ca_bundle_file" ]; then
            if cp "$system_ca_bundle" "$ca_runtime_dir/$ca_bundle_file" 2> /dev/null || sudo cp "$system_ca_bundle" "$ca_runtime_dir/$ca_bundle_file"; then
                log_success "Created CA certificate bundle in runtime directory"
      else
                log_warning "Could not create CA certificate bundle in runtime directory"
                return 1
      fi
    else
            log_info "CA certificate bundle already exists in runtime directory"
    fi
  else
        log_warning "System CA certificate bundle not found. SSL certificate validation may not work properly."
        return 1
  fi

    log_success "CA certificate bundle setup completed"
}

# Function to generate self-signed certificates for dev mode
generate_dev_certs() {
    log_info "Setting up self-signed certificates for dev mode..."

    local tls_dir="$APPS_IRC_ROOT/services/unrealircd/config/tls"
    local cert_domain="${IRC_DOMAIN:-localhost}"
    local live_dir="$tls_dir/live/$cert_domain"

    # Ensure directory exists
    mkdir -p "$live_dir"

    # Generate self-signed cert if it doesn't exist
    if [ ! -f "$live_dir/fullchain.pem" ] || [ ! -f "$live_dir/privkey.pem" ]; then
        log_info "Generating self-signed certificate for $cert_domain..."
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$live_dir/privkey.pem" \
            -out "$live_dir/fullchain.pem" \
            -subj "/CN=$cert_domain" \
            -addext "subjectAltName = DNS:$cert_domain, DNS:localhost, IP:127.0.0.1" 2>/dev/null

        log_success "Generated self-signed certificate for $cert_domain"
    else
        log_info "Self-signed certificate already exists for $cert_domain"
    fi

    # Also generate the legacy server.cert.pem/server.key.pem for compatibility if needed
    # (though we updated unrealircd.conf to use the live/localhost/ ones)
    if [ ! -f "$tls_dir/server.cert.pem" ]; then
        cp "$live_dir/fullchain.pem" "$tls_dir/server.cert.pem"
        cp "$live_dir/privkey.pem" "$tls_dir/server.key.pem"
        log_info "Created legacy certificate symlinks/copies"
    fi

    log_success "Dev certificate setup completed"
}

# Function to prepare configuration files from templates
prepare_config_files() {
    log_info "Preparing configuration files from templates..."

    # Load environment variables from .env if it exists
    if [ -f "$PROJECT_ROOT/.env" ]; then
        log_info "Loading environment variables from .env"
        # Use set -a to automatically export all variables
        set -a
        # shellcheck disable=SC1091
        source "$PROJECT_ROOT/.env"
        set +a
        log_info "Environment variables loaded"
  else
        log_warning ".env file not found. Configuration will use defaults."
        return 1
  fi

    # Check if envsubst is available
    if ! command -v envsubst > /dev/null 2>&1; then
        log_error "envsubst command not found. Please install gettext package."
        return 1
  fi

    # Prepare UnrealIRCd configuration
    local unreal_template="$APPS_IRC_ROOT/services/unrealircd/config/unrealircd.conf.template"
    local unreal_config="$APPS_IRC_ROOT/services/unrealircd/config/unrealircd.conf"

    if [ -f "$unreal_template" ]; then
        log_info "Creating UnrealIRCd configuration from template..."
        if envsubst < "$unreal_template" > "$unreal_config" 2> /dev/null; then
            log_success "UnrealIRCd configuration created"
    else
            log_warning "Could not create UnrealIRCd configuration (permission denied). Using existing file."
    fi
  elif   [ -f "$unreal_config" ]; then
        log_info "UnrealIRCd configuration already exists"
  else
        log_warning "No UnrealIRCd configuration template found"
  fi

    # Prepare Atheme configuration
    local atheme_template="$APPS_IRC_ROOT/services/atheme/config/atheme.conf.template"
    local atheme_config="$APPS_IRC_ROOT/services/atheme/config/atheme.conf"

    if [ -f "$atheme_template" ]; then
        log_info "Creating Atheme configuration from template..."
        envsubst < "$atheme_template" > "$atheme_config"
        log_success "Atheme configuration created"
  elif   [ -f "$atheme_config" ]; then
        log_info "Atheme configuration already exists"
  else
        log_warning "No Atheme configuration template found"
  fi

    # Show substituted values for verification
    log_info "Configuration values:"
    echo "  IRC_DOMAIN: ${IRC_DOMAIN:-'not set'}"
    echo "  IRC_NETWORK_NAME: ${IRC_NETWORK_NAME:-'not set'}"
    echo "  IRC_ADMIN_NAME: ${IRC_ADMIN_NAME:-'not set'}"
    echo "  ATHEME_SERVER_NAME: ${ATHEME_SERVER_NAME:-'not set'}"
    echo "  ATHEME_NETNAME: ${ATHEME_NETNAME:-'not set'}"
    echo "  ATHEME_ADMIN_NAME: ${ATHEME_ADMIN_NAME:-'not set'}"
    echo "  ATHEME_ADMIN_EMAIL: ${ATHEME_ADMIN_EMAIL:-'not set'}"
}

# Function to create .env template if it doesn't exist
create_env_template() {
    local env_file="$PROJECT_ROOT/.env"
    local env_example="$PROJECT_ROOT/env.example"

    if [ ! -f "$env_file" ] && [ -f "$env_example" ]; then
        cp "$env_example" "$env_file"
        log_info "Created .env file from template"
        log_warning "Please edit .env file with your configuration before starting services"
  elif   [ -f "$env_file" ]; then
        log_info ".env file already exists"
  else
        log_warning "No .env template found. You may need to create environment variables manually"
  fi
}

# Function to check Docker availability
check_docker() {
    log_info "Checking Docker availability..."

    if ! command -v docker > /dev/null 2>&1; then
        log_error "Docker is not installed or not in PATH"
        exit 1
  fi

    if ! command -v docker compose > /dev/null 2>&1 && ! docker compose version > /dev/null 2>&1; then
        log_error "Docker Compose is not available"
        exit 1
  fi

    log_success "Docker is available"
}

# Function to show next steps
show_next_steps() {
    echo ""
    log_info "Next steps:"
    echo "  1. Edit .env file with your configuration (optional)"
    echo "  3. Or run: docker compose up -d"
    echo ""
    log_info "Data will be stored in:"
    echo "  - $PROJECT_ROOT/data/ (persistent data)"
    echo "  - $PROJECT_ROOT/logs/ (log files)"
}

# Main function
main() {
    log_info "IRC Infrastructure Initialization"
    log_info "=================================="

    # Check if we're running as root (for permission info)
    if [ "$(id -u)" = "0" ]; then
        log_warning "Running as root - this is fine for initial setup"
  fi

    # Check Docker availability
    check_docker

    # Create directory structure
    create_directories

    # Set permissions
    set_permissions

    # Set up CA certificate bundle
    setup_ca_bundle

    # Generate dev certs
    generate_dev_certs

    # Create .env if needed
    create_env_template

    # Prepare configuration files from templates
    prepare_config_files

    # Show next steps
    show_next_steps

    log_success "Initialization completed successfully!"
}

# Run main function
if [[ ${BASH_SOURCE[0]} == "${0}" ]]; then
    main "$@"
fi
