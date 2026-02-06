#!/bin/bash
# shellcheck shell=bash

# Configuration Preparation Script
# Substitutes environment variables in UnrealIRCd configuration files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS_IRC_ROOT="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$(dirname "$APPS_IRC_ROOT")")"

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
  local unreal_config="$APPS_IRC_ROOT/services/unrealircd/config/unrealircd.conf"
  local atheme_config="$APPS_IRC_ROOT/services/atheme/config/atheme.conf"

  log_info "Preparing IRC configuration files with environment variables..."

  # Check if envsubst is available
  if ! command -v envsubst > /dev/null 2>&1; then
    log_error "envsubst command not found. Please install gettext package."
    exit 1
  fi

  # Load environment variables from .env if it exists
  if [ -f "$PROJECT_ROOT/.env" ]; then
    log_info "Loading environment variables from .env"
    # Use set -a to automatically export all variables
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env"
    set +a
    log_info "Environment variables loaded"
  fi

  # Prepare UnrealIRCd configuration
  local unreal_template="$APPS_IRC_ROOT/services/unrealircd/config/unrealircd.conf.template"
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
  local atheme_template="$APPS_IRC_ROOT/services/atheme/config/atheme.conf.template"
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
  echo "  ATHEME_SEND_PASSWORD: ${ATHEME_SEND_PASSWORD:-'not set'}"
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
