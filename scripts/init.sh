#!/bin/bash
# shellcheck shell=bash

# ATL Chat Infrastructure Initialization Script
# Creates required directory structure on host system

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables: .env (base) then .env.dev (overrides for just dev)
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env"
    set +a
fi
if [ -f "$PROJECT_ROOT/.env.dev" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env.dev"
    set +a
fi

# Ensure Atheme JSON-RPC port has a default (for existing .env without it)
export ATHEME_HTTPD_PORT="${ATHEME_HTTPD_PORT:-8081}"

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

    # Data directories (must match compose volume mounts)
    local data_dirs=(
        "$PROJECT_ROOT/data/irc/data"
        "$PROJECT_ROOT/data/irc/logs"
        "$PROJECT_ROOT/data/irc/webpanel-data"
        "$PROJECT_ROOT/data/atheme/data"
        "$PROJECT_ROOT/data/atheme/logs"
        "$PROJECT_ROOT/data/xmpp/data"
        "$PROJECT_ROOT/data/xmpp/logs"
        "$PROJECT_ROOT/data/xmpp/uploads"
        "$PROJECT_ROOT/data/certs"
    )

    # SSL/TLS: config/tls holds CA bundle only; server certs live in data/certs (mounted as certs/)
    local ssl_dirs=(
        "$PROJECT_ROOT/apps/unrealircd/config/tls"
    )

    # Create all directories
    for dir in "${data_dirs[@]}" "${ssl_dirs[@]}"; do
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

    # Set ownership for IRC data directory
    if [ -d "$PROJECT_ROOT/data/irc" ]; then
        sudo chown -R "$current_uid:$current_gid" "$PROJECT_ROOT/data/irc"
        chmod -R 755 "$PROJECT_ROOT/data/irc"
        log_info "Set permissions for IRC data directory"
  fi

    # Set ownership for Atheme data directory with correct UID
    if [ -d "$PROJECT_ROOT/data/atheme" ]; then
        sudo chown -R "$atheme_uid:$atheme_gid" "$PROJECT_ROOT/data/atheme"
        chmod 755 "$PROJECT_ROOT/data/atheme"
        log_info "Set permissions for Atheme data directory"
  fi

    # Set ownership for UnrealIRCd logs
    if [ -d "$PROJECT_ROOT/data/irc/logs" ]; then
        sudo chown -R "$current_uid:$current_gid" "$PROJECT_ROOT/data/irc/logs"
        chmod 755 "$PROJECT_ROOT/data/irc/logs"
        log_info "Set ownership for UnrealIRCd logs"
    fi

    # Set ownership for Atheme logs with correct UID
    if [ -d "$PROJECT_ROOT/data/atheme/logs" ]; then
        sudo chown -R "$atheme_uid:$atheme_gid" "$PROJECT_ROOT/data/atheme/logs"
        chmod 755 "$PROJECT_ROOT/data/atheme/logs"
        log_info "Set permissions for Atheme logs directory"
    fi

    # Set permissions for SSL certificates
    if [ ! -d "$PROJECT_ROOT/apps/unrealircd/config/tls" ]; then
        sudo mkdir -p "$PROJECT_ROOT/apps/unrealircd/config/tls"
    fi
    sudo chown "$current_uid:$current_gid" "$PROJECT_ROOT/apps/unrealircd/config/tls" 2> /dev/null || true
    chmod 755 "$PROJECT_ROOT/apps/unrealircd/config/tls" || sudo chmod 755 "$PROJECT_ROOT/apps/unrealircd/config/tls" || log_warning "Could not set permissions for SSL directory"
    log_info "Set permissions for SSL directory"

    # Make sure data directories are writable
    find "$PROJECT_ROOT/data" -type d -exec chmod 755 {} \; 2> /dev/null || true
    find "$PROJECT_ROOT/data/atheme" -type d -exec chmod 755 {} \; 2> /dev/null || true

    log_success "Permissions set successfully"
}

# Function to set up CA certificate bundle
setup_ca_bundle() {
    log_info "Setting up CA certificate bundle..."

    local ca_template_dir="$PROJECT_ROOT/docs/examples/unrealircd/tls"
    local ca_runtime_dir="$PROJECT_ROOT/apps/unrealircd/config/tls"
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

    # Remove obsolete cert files from config/tls (server certs now live in data/certs)
    rm -f "$ca_runtime_dir/server.cert.pem" "$ca_runtime_dir/server.key.pem" 2>/dev/null || true
    rm -rf "$ca_runtime_dir/live" 2>/dev/null || true

    log_success "CA certificate bundle setup completed"
}

# Function to generate self-signed certificates for dev mode
generate_cert() {
    local domain="$1"
    local base_dir="$2"
    local live_dir="$base_dir/live/$domain"

    # Ensure directory exists
    mkdir -p "$live_dir"

    # Generate self-signed cert if it doesn't exist
    if [ ! -f "$live_dir/fullchain.pem" ] || [ ! -f "$live_dir/privkey.pem" ]; then
        log_info "Generating self-signed certificate for $domain..."
        # SANs: main, wildcard, Prosody components (muc/upload/proxy/pubsub/bridge), localhost
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$live_dir/privkey.pem" \
            -out "$live_dir/fullchain.pem" \
            -subj "/CN=$domain" \
            -addext "subjectAltName=DNS:$domain,DNS:*.$domain,DNS:muc.$domain,DNS:upload.$domain,DNS:proxy.$domain,DNS:pubsub.$domain,DNS:bridge.$domain,DNS:localhost,IP:127.0.0.1" 2>/dev/null

        log_success "Generated self-signed certificate for $domain"
    else
        log_info "Self-signed certificate already exists for $domain"
    fi

    # Ensure privkey is readable by container user (openssl defaults to 0600; container runs as PUID)
    chmod 644 "$live_dir/privkey.pem" 2>/dev/null || sudo chmod 644 "$live_dir/privkey.pem" 2>/dev/null || true
}

generate_dev_certs() {
    log_info "Setting up self-signed certificates for dev mode..."

    # IRC and XMPP both use data/certs (Let's Encrypt layout: live/<domain>/fullchain.pem, privkey.pem)
    local shared_cert_dir="$PROJECT_ROOT/data/certs"
    generate_cert "${IRC_DOMAIN:-irc.localhost}" "$shared_cert_dir"
    generate_cert "${PROSODY_DOMAIN:-xmpp.localhost}" "$shared_cert_dir"

    log_success "Dev certificate setup completed"
}

# Function to prepare configuration files from templates
prepare_config_files() {
    log_info "Preparing configuration files from templates..."

    # Load environment variables from .env if it exists
    if [ -f "$PROJECT_ROOT/.env" ]; then
        log_info "Loading environment variables from .env"
        set -a
        # shellcheck disable=SC1091
        source "$PROJECT_ROOT/.env"
        set +a
        log_info "Environment variables loaded"
    fi

    # IRC cert paths: use shared data/certs (Let's Encrypt layout), matching Prosody
    export IRC_SSL_CERT_PATH="${IRC_SSL_CERT_PATH:-/home/unrealircd/unrealircd/certs/live/${IRC_DOMAIN:-irc.localhost}/fullchain.pem}"
    export IRC_SSL_KEY_PATH="${IRC_SSL_KEY_PATH:-/home/unrealircd/unrealircd/certs/live/${IRC_DOMAIN:-irc.localhost}/privkey.pem}"

    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_warning ".env file not found. Configuration will use defaults."
        return 1
  fi

    # Check if envsubst is available
    if ! command -v envsubst > /dev/null 2>&1; then
        log_error "envsubst command not found. Please install gettext package."
        return 1
  fi

    # Prepare UnrealIRCd configuration
    local unreal_template="$PROJECT_ROOT/apps/unrealircd/config/unrealircd.conf.template"
    local unreal_config="$PROJECT_ROOT/apps/unrealircd/config/unrealircd.conf"

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
    local atheme_template="$PROJECT_ROOT/apps/atheme/config/atheme.conf.template"
    local atheme_config="$PROJECT_ROOT/apps/atheme/config/atheme.conf"

    if [ -f "$atheme_template" ]; then
        log_info "Creating Atheme configuration from template..."
        envsubst < "$atheme_template" > "$atheme_config"
        log_success "Atheme configuration created"
  elif   [ -f "$atheme_config" ]; then
        log_info "Atheme configuration already exists"
  else
        log_warning "No Atheme configuration template found"
  fi

    # Run prepare-config.sh (UnrealIRCd, Atheme, Bridge config from templates)
    if [ -f "$SCRIPT_DIR/prepare-config.sh" ]; then
        log_info "Running prepare-config.sh (bridge config, etc.)..."
        # shellcheck source=prepare-config.sh
        "$SCRIPT_DIR/prepare-config.sh" || log_warning "prepare-config.sh reported issues"
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
    local env_example="$PROJECT_ROOT/.env.example"

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
    echo "  - $PROJECT_ROOT/data/ (persistent data: irc/, atheme/, xmpp/, certs/)"
}

# Main function
main() {
    log_info "ATL Chat Infrastructure Initialization"
    log_info "======================================"

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
