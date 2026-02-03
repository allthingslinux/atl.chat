#!/bin/bash
# Auto-create admin user for development
# This script creates the admin@localhost user if it doesn't exist

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [[ -f "${PROJECT_DIR}/.env.development" ]]; then
    # shellcheck source=/dev/null
    source "${PROJECT_DIR}/.env.development"
fi

# Set defaults
PROSODY_ADMIN_JID="${PROSODY_ADMIN_JID:-admin@localhost}"
PROSODY_ADMIN_PASSWORD="${PROSODY_ADMIN_PASSWORD:-devpassword123}"

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

# Check if we're running in Docker
is_docker_environment() {
    [[ -f /.dockerenv ]] || grep -q docker /proc/1/cgroup 2> /dev/null
}

# Get container name
get_container_name() {
    for name in "xmpp-prosody-dev" "xmpp-prosody-1" "xmpp-prosody"; do
        if docker ps --format "{{.Names}}" | grep -q "^${name}$"; then
            echo "$name"
            return 0
        fi
    done

    local container_name
    container_name=$(docker ps --format "{{.Names}}" | grep prosody | head -1)
    if [[ -n "$container_name" ]]; then
        echo "$container_name"
        return 0
    fi

    echo "xmpp-prosody-dev" # Default fallback
}

# Run command in container
run_in_container() {
    if is_docker_environment; then
        "$@"
    else
        if ! docker ps --format "{{.Names}}" 2> /dev/null | grep -q prosody; then
            log_warn "No Prosody container running"
            return 1
        fi
        docker exec "$(get_container_name)" "$@"
    fi
}

# Wait for Prosody to be ready
wait_for_prosody() {
    log_info "Waiting for Prosody to be ready..."

    # Try to connect to Prosody port instead of using prosodyctl
    for _ in {1..30}; do
        if timeout 1 bash -c "echo >/dev/tcp/xmpp-prosody-dev/5222" 2> /dev/null; then
            log_success "Prosody is ready (port 5222 is open)"
            return 0
        fi
        sleep 1
    done

    log_error "Prosody failed to start within 30 seconds"
    return 1
}

# Create admin user
create_admin_user() {
    local jid="$1"
    local password="$2"

    log_info "Checking if admin user exists: $jid"

    # Extract username and domain from JID
    local username domain
    if [[ "$jid" =~ ^([^@]+)@(.+)$ ]]; then
        username="${BASH_REMATCH[1]}"
        domain="${BASH_REMATCH[2]}"
    else
        log_error "Invalid JID format: $jid"
        return 1
    fi

    # Check if user exists
    if run_in_container prosodyctl getpassword "$username" "$domain" > /dev/null 2>&1; then
        log_warn "Admin user $jid already exists"
        return 0
    fi

    log_info "Creating admin user: $jid"

    # Create the user
    if run_in_container prosodyctl adduser "$username@$domain" <<< "$password
$password" 2> /dev/null; then
        log_success "Admin user created successfully: $jid"
        return 0
    else
        log_error "Failed to create admin user: $jid"
        return 1
    fi
}

# Main function
main() {
    echo "Admin User Auto-Creation Script"
    echo "==============================="
    echo ""

    # Wait for Prosody to be ready
    if ! wait_for_prosody; then
        exit 1
    fi

    # Create admin user
    if create_admin_user "$PROSODY_ADMIN_JID" "$PROSODY_ADMIN_PASSWORD"; then
        echo ""
        log_success "Admin user setup completed!"
        echo "JID: $PROSODY_ADMIN_JID"
        echo "Password: $PROSODY_ADMIN_PASSWORD"
        echo ""
        echo "You can now log in to the admin interface and XMPP clients"
        echo "with these credentials."
    else
        echo ""
        log_error "Failed to set up admin user"
        exit 1
    fi
}

# Run main function
main "$@"
