#!/bin/bash
# shellcheck shell=bash

# ============================================================================
# IRC OPERATOR PASSWORD GENERATOR
# ============================================================================
# Generate secure password hashes for IRC operators
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Repo root: apps/unrealircd/scripts -> apps/unrealircd -> apps -> repo root
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to generate password hash
generate_password() {
  local container_name="$1"

  if ! (cd "$PROJECT_ROOT" && docker compose ps "$container_name") | grep -q "Up"; then
    log_error "Container '$container_name' is not running"
    log_info "Start the container first with: docker compose up -d (from repo root)"
    exit 1
  fi

  log_info "Generating Argon2 password hash (recommended by UnrealIRCd)..."
  log_info "You will be prompted to enter your desired password"
  log_info "(The password will not be displayed as you type)"
  echo

  # Generate the hash using the container's unrealircd mkpasswd argon2 command
  # -it: interactive TTY so user can type password securely (no echo)
  # argon2: recommended auth type per UnrealIRCd Authentication types docs
  local raw_output hash
  raw_output=$(cd "$PROJECT_ROOT" && docker compose exec -it "$container_name" /home/unrealircd/unrealircd/unrealircd mkpasswd argon2)
  # Extract Argon2 hash (mkpasswd may print "Encrypted password is: $argon2id$...")
  # shellcheck disable=SC2016
  hash=$(echo "$raw_output" | grep -oE '\$argon2[^[:space:]]*' | head -1)
  hash=${hash:-$raw_output}
  if [ -n "$hash" ] && [[ "$hash" == *"argon2"* ]]; then
    log_success "Password hash generated successfully!"
    echo
    echo "================================================================="
    echo "IRC OPERATOR PASSWORD HASH:"
    echo "================================================================="
    echo "$hash"
    echo "================================================================="
    echo
    log_info "Add this hash to your .env file:"
    echo "IRC_OPER_PASSWORD=\"$hash\""
    echo
    log_info "Or update your .env file directly:"
    echo "echo 'IRC_OPER_PASSWORD=\"$hash\"' >> .env"
    echo
    log_warning "Make sure .env is in your .gitignore file!"
  else
    log_error "Failed to generate password hash"
    exit 1
  fi
}

# Function to show usage
show_usage() {
  echo "IRC Operator Password Generator"
  echo "==============================="
  echo
  echo "Usage:"
  echo "  $0 [container-name]"
  echo
  echo "Arguments:"
  echo "  container-name    Name of the IRC container (default: atl-irc-server)"
  echo
  echo "Examples:"
  echo "  $0                # Use default container 'atl-irc-server'"
  echo "  $0 atl-irc-server # Use container 'atl-irc-server'"
  echo
  echo "Requirements:"
  echo "  - IRC container must be running"
  echo "  - Docker Compose setup must be available"
  echo
  echo "After generating the hash:"
  echo "  1. Copy the hash from the output"
  echo "  2. Add it to your .env file:"
  # shellcheck disable=SC2016
  echo '     IRC_OPER_PASSWORD="$hash"'
  echo "  3. Regenerate config from template (run from repo root):"
  echo "     bash scripts/prepare-config.sh"
  echo "  4. Rehash IRCd (as IRCOp): /REHASH  or restart (from repo root): docker compose restart atl-irc-server"
}

# Main function
main() {
  local container_name="${1:-atl-irc-server}"

  # Show usage if requested
  if [[ ${1:-} == "--help" ]] || [[ ${1:-} == "-h" ]]; then
    show_usage
    exit 0
  fi

  log_info "IRC Operator Password Generator"
  log_info "==============================="
  echo

  # Require root compose.yaml
  if [[ ! -f "$PROJECT_ROOT/compose.yaml" ]]; then
    log_error "compose.yaml not found at $PROJECT_ROOT"
    exit 1
  fi

  # Generate the password
  generate_password "$container_name"
}

# Run main function
if [[ ${BASH_SOURCE[0]} == "${0}" ]]; then
  main "$@"
fi
