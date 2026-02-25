#!/bin/bash
# shellcheck shell=bash

# Configuration Preparation Script
# Substitutes environment variables in UnrealIRCd and Atheme configuration files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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

# Function to prepare configuration
prepare_config() {
  local unreal_config="$PROJECT_ROOT/apps/unrealircd/config/unrealircd.conf"
  local atheme_config="$PROJECT_ROOT/apps/atheme/config/atheme.conf"

  log_info "Preparing IRC configuration files with environment variables..."

  # Check if envsubst is available
  if ! command -v envsubst > /dev/null 2>&1; then
    log_error "envsubst command not found. Please install gettext package."
    exit 1
  fi

  # Load .env (base) then .env.dev (overrides for just dev)
  if [ -f "$PROJECT_ROOT/.env" ]; then
    log_info "Loading environment variables from .env"
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env"
    set +a
  fi
  if [ -f "$PROJECT_ROOT/.env.dev" ]; then
    log_info "Loading .env.dev overrides"
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env.dev"
    set +a
  fi
  if [ -f "$PROJECT_ROOT/.env" ] || [ -f "$PROJECT_ROOT/.env.dev" ]; then
    log_info "Environment variables loaded"
  fi

  # Ensure Atheme JSON-RPC port has a default (for existing .env without it)
  export ATHEME_HTTPD_PORT="${ATHEME_HTTPD_PORT:-8081}"

  # The Lounge: WebIRC password (must match UnrealIRCd proxy block); TLS verify; janitor retention
  export THELOUNGE_WEBIRC_PASSWORD="${THELOUNGE_WEBIRC_PASSWORD:-change_me_thelounge_webirc}"
  export THELOUNGE_DELETE_UPLOADS_AFTER_MINUTES="${THELOUNGE_DELETE_UPLOADS_AFTER_MINUTES:-1440}"
  IRC_LOUNGE_REJECT_UNAUTHORIZED="$([ "${ATL_ENVIRONMENT:-}" = "dev" ] && echo "false" || echo "true")"
  export IRC_LOUNGE_REJECT_UNAUTHORIZED

  # Bridge: IRC server hostname inside Docker network; Prosody domain for MUC JID
  export IRC_BRIDGE_SERVER="${IRC_BRIDGE_SERVER:-atl-irc-server}"
  export BRIDGE_IRC_OPER_PASSWORD="${BRIDGE_IRC_OPER_PASSWORD:-change_me_bridge_oper}"
  export PROSODY_DOMAIN="${PROSODY_DOMAIN:-${XMPP_DOMAIN:-xmpp.localhost}}"
  # Discord channel ID for bridge mappings (set in .env to survive prepare-config runs)
  export BRIDGE_DISCORD_CHANNEL_ID="${BRIDGE_DISCORD_CHANNEL_ID:-REPLACE_WITH_DISCORD_CHANNEL_ID}"
  # IRC TLS verify: false for dev (self-signed certs), true for prod
  export IRC_TLS_VERIFY="${BRIDGE_IRC_TLS_VERIFY:-${IRC_TLS_VERIFY:-$([ "${ATL_ENVIRONMENT:-}" = "dev" ] && echo "false" || echo "true")}}"

  # IRC cert paths: use shared data/certs (Let's Encrypt layout), matching Prosody
  export IRC_SSL_CERT_PATH="${IRC_SSL_CERT_PATH:-/home/unrealircd/unrealircd/certs/live/${IRC_DOMAIN:-irc.localhost}/fullchain.pem}"
  export IRC_SSL_KEY_PATH="${IRC_SSL_KEY_PATH:-/home/unrealircd/unrealircd/certs/live/${IRC_DOMAIN:-irc.localhost}/privkey.pem}"

  # IRC log path: must match compose volume mount (data/irc/logs -> /home/unrealircd/unrealircd/logs)
  export IRC_LOG_PATH="${IRC_LOG_PATH:-/home/unrealircd/unrealircd/logs}"

  # Cloak keys (fallback to example keys for dev if unset - regenerate for production)
  export IRC_CLOAK_KEY_1="${IRC_CLOAK_KEY_1:-daa0ad2a69ba7683a2cdb02499f2e98b0729423bb7578d1f1dfbcdfe015f1f8b554b13203289c83D}"
  export IRC_CLOAK_KEY_2="${IRC_CLOAK_KEY_2:-899874eda706ee805bd34792bfd7bd62711f1938dea920c8bdf8396fe136ab6a83785a3ce54eB298}"
  export IRC_CLOAK_KEY_3="${IRC_CLOAK_KEY_3:-d8936d8fff38eace5c379c94578abfa802088bd241329c64506513fe8e4de3e2304f7dd00355A8d6}"

  # Prepare UnrealIRCd configuration
  local unreal_template="$PROJECT_ROOT/apps/unrealircd/config/unrealircd.conf.template"
  if [ -f "$unreal_template" ]; then
    log_info "Preparing UnrealIRCd configuration from template..."

    # Make target file writable if it exists and we own it, or remove it if we don't
    if [ -f "$unreal_config" ]; then
      if [ -w "$unreal_config" ] || chmod 644 "$unreal_config" 2> /dev/null; then
        log_info "Made existing config file writable"
      else
        log_info "Cannot modify existing config file, will overwrite with sudo"
        sudo rm -f "$unreal_config" 2> /dev/null || rm -f "$unreal_config" 2> /dev/null || true
      fi
    fi

    # Always use temp file approach for reliability
    local temp_file="/tmp/unrealircd.conf.tmp"
    envsubst < "$unreal_template" > "$temp_file"

    # Try different copy strategies
    if cp "$temp_file" "$unreal_config" 2> /dev/null; then
      log_info "Configuration written successfully"
    elif sudo cp "$temp_file" "$unreal_config" 2> /dev/null; then
      log_info "Configuration written with sudo"
    else
      log_warning "Could not write configuration file - using existing"
    fi

    rm -f "$temp_file"
    log_success "UnrealIRCd configuration prepared from template"
  elif [ -f "$unreal_config" ]; then
    log_info "Preparing UnrealIRCd configuration..."

    # Make file writable first
    chmod 644 "$unreal_config" 2> /dev/null || sudo chmod 644 "$unreal_config" 2> /dev/null || true

    local temp_file="/tmp/unrealircd.conf.tmp"
    envsubst < "$unreal_config" > "$temp_file"
    cp "$temp_file" "$unreal_config"
    rm -f "$temp_file"
    log_success "UnrealIRCd configuration prepared"
  else
    log_warning "UnrealIRCd configuration file not found: $unreal_config"
    log_warning "Template file not found: $unreal_template"
  fi

  # Prepare Atheme configuration
  local atheme_template="$PROJECT_ROOT/apps/atheme/config/atheme.conf.template"
  if [ -f "$atheme_template" ]; then
    log_info "Preparing Atheme configuration from template..."

    # Make target file writable if it exists
    if [ -f "$atheme_config" ]; then
      chmod 644 "$atheme_config" 2> /dev/null || sudo chmod 644 "$atheme_config" 2> /dev/null || true
    fi

    local temp_file="/tmp/atheme.conf.tmp"
    envsubst < "$atheme_template" > "$temp_file"
    cp "$temp_file" "$atheme_config"
    rm -f "$temp_file"
    log_success "Atheme configuration prepared from template"
  elif [ -f "$atheme_config" ]; then
    log_info "Preparing Atheme configuration..."

    # Make file writable first
    chmod 644 "$atheme_config" 2> /dev/null || sudo chmod 644 "$atheme_config" 2> /dev/null || true

    local temp_file="/tmp/atheme.conf.tmp"
    envsubst < "$atheme_config" > "$temp_file"
    cp "$temp_file" "$atheme_config"
    rm -f "$temp_file"
    log_success "Atheme configuration prepared"
  else
    log_warning "Atheme configuration file not found: $atheme_config"
    log_warning "Template file not found: $atheme_template"
  fi

  # Prepare bridge configuration
  local bridge_config="$PROJECT_ROOT/apps/bridge/config.yaml"
  local bridge_template="$PROJECT_ROOT/apps/bridge/config.template.yaml"
  if [ -f "$bridge_template" ]; then
    log_info "Preparing bridge configuration from template..."
    local temp_file="/tmp/bridge-config.yaml.tmp"
    envsubst < "$bridge_template" > "$temp_file"
    if cp "$temp_file" "$bridge_config" 2>/dev/null || sudo cp "$temp_file" "$bridge_config" 2>/dev/null; then
      log_success "Bridge configuration prepared"
    else
      log_warning "Could not write bridge config to $bridge_config"
    fi
    rm -f "$temp_file"
  elif [ ! -f "$bridge_config" ]; then
    log_warning "Bridge config not found. Copy apps/bridge/config.example.yaml to apps/bridge/config.yaml and customize."
    if [ -f "$PROJECT_ROOT/apps/bridge/config.example.yaml" ]; then
      cp "$PROJECT_ROOT/apps/bridge/config.example.yaml" "$bridge_config" 2>/dev/null || true
      log_info "Copied config.example.yaml to apps/bridge/config.yaml - edit with your Discord channel ID"
    fi
  fi

  # Prepare The Lounge configuration
  local lounge_template="$PROJECT_ROOT/apps/thelounge/config.js.template"
  local lounge_config="$PROJECT_ROOT/data/thelounge/config.js"
  if [ -f "$lounge_template" ]; then
    log_info "Preparing The Lounge configuration from template..."
    mkdir -p "$(dirname "$lounge_config")"
    local temp_file="/tmp/thelounge-config.js.tmp"
    envsubst < "$lounge_template" > "$temp_file"
    if cp "$temp_file" "$lounge_config" 2>/dev/null || sudo cp "$temp_file" "$lounge_config" 2>/dev/null; then
      log_success "The Lounge configuration prepared"
    else
      log_warning "Could not write The Lounge config to $lounge_config"
    fi
    rm -f "$temp_file"
  fi

  log_success "All configuration files prepared successfully"

  # Show substituted values for verification
  log_info "Substituted values:"
  echo "  IRC_DOMAIN: ${IRC_DOMAIN:-'not set'}"
  echo "  IRC_NETWORK_NAME: ${IRC_NETWORK_NAME:-'not set'}"
  echo "  IRC_CLOAK_PREFIX: ${IRC_CLOAK_PREFIX:-'not set'}"
  echo "  IRC_ADMIN_NAME: ${IRC_ADMIN_NAME:-'not set'}"
  echo "  IRC_ADMIN_EMAIL: ${IRC_ADMIN_EMAIL:-'not set'}"
  echo "  IRC_SERVICES_SERVER: ${IRC_SERVICES_SERVER:-'not set'}"
  echo "  IRC_ROOT_DOMAIN: ${IRC_ROOT_DOMAIN:-'not set'}"
  echo "  IRC_SERVICES_PASSWORD: ${IRC_SERVICES_PASSWORD:-'not set'}"
  echo "  IRC_OPER_PASSWORD: ${IRC_OPER_PASSWORD:-'not set'}"
  echo "  ATHEME_SERVER_NAME: ${ATHEME_SERVER_NAME:-'not set'}"
  echo "  ATHEME_UPLINK_HOST: ${ATHEME_UPLINK_HOST:-'not set'}"
  echo "  ATHEME_UPLINK_PORT: ${ATHEME_UPLINK_PORT:-'not set'}"
  echo "  ATHEME_HTTPD_PORT: ${ATHEME_HTTPD_PORT:-8081}"
  echo "  ATHEME_SEND_PASSWORD: ${ATHEME_SEND_PASSWORD:-'not set'}"
  echo "  BRIDGE_XMPP_COMPONENT_JID: ${BRIDGE_XMPP_COMPONENT_JID:-'not set'}"
  echo "  BRIDGE_XMPP_COMPONENT_SERVER: ${BRIDGE_XMPP_COMPONENT_SERVER:-'not set'}"
  echo "  PROSODY_DOMAIN: ${PROSODY_DOMAIN:-'not set'}"
}

# Main function
main() {
  log_info "IRC Configuration Preparation"

  # Check if we're in a container environment
  if [ -f /.dockerenv ]; then
    log_info "Running in container environment"
  fi

  prepare_config
}

# Run main function
if [[ ${BASH_SOURCE[0]} == "${0}" ]]; then
  main "$@"
fi
