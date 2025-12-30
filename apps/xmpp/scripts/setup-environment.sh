#!/bin/bash

# Environment Setup Script
# Helps set up environment-specific configuration files

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

# Function to setup environment
setup_environment() {
    local env_type="$1"
    local template_file="$PROJECT_ROOT/.env.example"
    local target_file="$PROJECT_ROOT/.env.$env_type"

    if [ ! -f "$template_file" ]; then
        log_error "Template file not found: $template_file"
        exit 1
    fi

    if [ -f "$target_file" ]; then
        log_warning "Environment file already exists: $target_file"
        read -p "Do you want to overwrite it? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Skipping $env_type environment setup"
            return
        fi
    fi

    log_info "Setting up $env_type environment..."

    # Copy template
    cp "$template_file" "$target_file"

    # Environment-specific modifications
    case "$env_type" in
        "development")
            # Development-specific settings
            sed -i 's/PROSODY_ENV=.*/PROSODY_ENV=development/' "$target_file"
            sed -i 's/PROSODY_DOMAIN=.*/PROSODY_DOMAIN=localhost/' "$target_file"
            sed -i 's/PROSODY_HTTP_SCHEME=.*/PROSODY_HTTP_SCHEME=http/' "$target_file"
            sed -i 's/PROSODY_DB_HOST=.*/PROSODY_DB_HOST=xmpp-postgres-dev/' "$target_file"
            sed -i 's/PROSODY_DB_PASSWORD=.*/PROSODY_DB_PASSWORD=devpassword/' "$target_file"
            sed -i 's/PROSODY_ALLOW_REGISTRATION=.*/PROSODY_ALLOW_REGISTRATION=true/' "$target_file"
            sed -i 's/PROSODY_C2S_REQUIRE_ENCRYPTION=.*/PROSODY_C2S_REQUIRE_ENCRYPTION=false/' "$target_file"
            sed -i 's/PROSODY_LOG_LEVEL=.*/PROSODY_LOG_LEVEL=debug/' "$target_file"
            sed -i 's/PROSODY_ARCHIVE_EXPIRES_AFTER=.*/PROSODY_ARCHIVE_EXPIRES_AFTER=30d/' "$target_file"
            ;;

        "production")
            # Production-specific settings
            sed -i 's/PROSODY_ENV=.*/PROSODY_ENV=production/' "$target_file"
            sed -i 's/PROSODY_DOMAIN=.*/PROSODY_DOMAIN=your-domain.com/' "$target_file"
            sed -i 's/PROSODY_HTTP_SCHEME=.*/PROSODY_HTTP_SCHEME=https/' "$target_file"
            sed -i 's/PROSODY_DB_HOST=.*/PROSODY_DB_HOST=xmpp-postgres/' "$target_file"
            sed -i 's/PROSODY_DB_PASSWORD=.*/PROSODY_DB_PASSWORD=CHANGE_THIS_TO_A_SECURE_PASSWORD/' "$target_file"
            sed -i 's/PROSODY_ALLOW_REGISTRATION=.*/PROSODY_ALLOW_REGISTRATION=false/' "$target_file"
            sed -i 's/PROSODY_C2S_REQUIRE_ENCRYPTION=.*/PROSODY_C2S_REQUIRE_ENCRYPTION=true/' "$target_file"
            sed -i 's/PROSODY_LOG_LEVEL=.*/PROSODY_LOG_LEVEL=info/' "$target_file"
            sed -i 's/PROSODY_RESTRICT_ROOM_CREATION=.*/PROSODY_RESTRICT_ROOM_CREATION=true/' "$target_file"
            sed -i 's/PROSODY_MUC_DEFAULT_PUBLIC=.*/PROSODY_MUC_DEFAULT_PUBLIC=false/' "$target_file"
            ;;

    esac

    log_success "Created $target_file"
    log_warning "Please edit $target_file with your specific values before running!"
}

# Main menu
show_menu() {
    echo "=========================================="
    echo "XMPP Server Environment Setup"
    echo "=========================================="
    echo "1. Setup Development Environment"
    echo "2. Setup Production Environment"
    echo "3. Setup All Environments"
    echo "4. Exit"
    echo "=========================================="
}

# Main logic
main() {
    log_info "XMPP Server Environment Setup"
    log_info "Project root: $PROJECT_ROOT"

    # Check for non-interactive mode
    if [[ "${1:-}" == "--non-interactive" ]]; then
        case "${2:-}" in
            "development")
                setup_environment "development"
                exit 0
                ;;
            "production")
                setup_environment "production"
                exit 0
                ;;
            "all")
                log_info "Setting up all environments..."
                setup_environment "development"
                setup_environment "production"
                log_success "All environments configured!"
                exit 0
                ;;
            *)
                log_error "Usage: $0 --non-interactive [development|production|all]"
                exit 1
                ;;
        esac
    fi

    while true; do
        show_menu
        read -r -p "Select an option (1-4): " choice

        case $choice in
            1)
                setup_environment "development"
                ;;
            2)
                setup_environment "production"
                ;;
            3)
                log_info "Setting up all environments..."
                setup_environment "development"
                setup_environment "production"
                log_success "All environments configured!"
                ;;
            4)
                log_info "Exiting..."
                exit 0
                ;;
            *)
                log_error "Invalid option. Please choose 1-4."
                ;;
        esac

        echo
        read -r -p "Press Enter to continue..."
        clear
    done
}

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
