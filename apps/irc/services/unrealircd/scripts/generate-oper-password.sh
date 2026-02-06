#!/bin/bash
# shellcheck shell=bash

# ============================================================================
# IRC OPERATOR PASSWORD GENERATOR
# ============================================================================
# Generate secure password hashes for IRC operators
# ============================================================================

set -euo pipefail

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

  if ! docker compose ps "$container_name" | grep -q "Up"; then
    log_error "Container '$container_name' is not running"
    log_info "Start the container first with: docker compose up -d"
    exit 1
  fi

  log_info "Generating secure password hash..."
  log_info "You will be prompted to enter your desired password"
  log_info "(The password will not be displayed as you type)"
  echo

  # Generate the hash using the container's unrealircd mkpasswd command
  local hash
  if hash=$(docker compose exec -T "$container_name" /home/unrealircd/unrealircd/unrealircd mkpasswd) && [ -n "$hash" ]; then
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
  echo '     IRC_OPER_PASSWORD="$hash"'
  echo "  3. Restart the IRC container:"
  echo "     docker compose restart atl-irc-server"
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

  # Check if we're in the right directory
  if [[ ! -f "compose.yaml" ]] && [[ ! -f "docker-compose.yml" ]]; then
    log_error "No compose.yaml or docker-compose.yml found in current directory"
    log_info "Make sure you're in the IRC project root directory"
    exit 1
  fi

  # Generate the password
  generate_password "$container_name"
}

# Run main function
if [[ ${BASH_SOURCE[0]} == "${0}" ]]; then
  main "$@"
fi
