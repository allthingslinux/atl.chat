#!/bin/bash
# UnrealIRCd Contrib Modules Management Script
# Provides an easy interface to install, manage, and configure 3rd party modules
# Based on the official UnrealIRCd module manager documentation

set -euo pipefail

# Color definitions for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
UNREALIRCD_BIN="/home/unrealircd/unrealircd/unrealircd"
UNREALIRCD_DIR="/home/unrealircd/unrealircd"
CONTRIB_DIR="/home/unrealircd/unrealircd/contrib"
MODULES_DIR="/home/unrealircd/unrealircd/modules"
CONFIG_DIR="/home/unrealircd/unrealircd/config"

# Print functions
print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_header() { echo -e "${PURPLE}=== $1 ===${NC}"; }

# Check if we're running as the correct user (unrealircd, typically UID from PUID)
check_user() {
    local expected_uid="${PUID:-1000}"
    if [ "$(id -u)" != "$expected_uid" ]; then
        print_error "This script must run as the unrealircd user (UID ${expected_uid})"
        print_error "Current user: $(id -un) (UID $(id -u))"
        exit 1
    fi
}

# Check if UnrealIRCd is running
check_unrealircd_running() {
    if pgrep -f unrealircd >/dev/null; then
        print_warning "UnrealIRCd is currently running"
        print_warning "Some operations may require a restart to take effect"
        return 0
    else
        print_status "UnrealIRCd is not currently running"
        return 1
    fi
}

# List available modules
list_modules() {
    print_header "Available Contrib Modules"

    if [ ! -d "$CONTRIB_DIR" ]; then
        print_error "Contrib directory not found: $CONTRIB_DIR"
        return 1
    fi

    cd "$UNREALIRCD_DIR" || exit 1

    print_status "Fetching latest module list..."
    if [ -d "$CONTRIB_DIR" ]; then
        cd "$CONTRIB_DIR" && git pull --quiet origin main 2>/dev/null || true
    fi

    cd "$UNREALIRCD_DIR" || exit 1

    print_status "Available modules:"
    echo
    "$UNREALIRCD_BIN" module list 2>/dev/null || {
        print_warning "Module manager not available, showing contrib directory contents:"
        for item in "$CONTRIB_DIR"/*; do
            if [ -d "$item" ] && [ "$(basename "$item")" != "*" ]; then
                basename "$item"
            fi
        done | sort
    }
}

# Show module information
show_module_info() {
    local module_name="$1"

    if [ -z "$module_name" ]; then
        print_error "Module name required"
        print_error "Usage: $0 info <module-name>"
        return 1
    fi

    print_header "Module Information: $module_name"

    cd "$UNREALIRCD_DIR" || exit 1

    # Try to get info via module manager first
    if "$UNREALIRCD_BIN" module info "third/$module_name" 2>/dev/null; then
        return 0
    fi

    # Fallback to showing contrib directory info
    if [ -d "$CONTRIB_DIR/$module_name" ]; then
        print_status "Module found in contrib directory:"
        ls -la "$CONTRIB_DIR/$module_name"

        if [ -f "$CONTRIB_DIR/$module_name/README.md" ]; then
            echo
            print_status "README content:"
            cat "$CONTRIB_DIR/$module_name/README.md"
        fi

        if [ -f "$CONTRIB_DIR/$module_name/README" ]; then
            echo
            print_status "README content:"
            cat "$CONTRIB_DIR/$module_name/README"
        fi
    else
        print_error "Module '$module_name' not found in contrib directory"
        return 1
    fi
}

# Install a module
install_module() {
    local module_name="$1"

    if [ -z "$module_name" ]; then
        print_error "Module name required"
        print_error "Usage: $0 install <module-name>"
        return 1
    fi

    print_header "Installing Module: $module_name"

    cd "$UNREALIRCD_DIR" || exit 1

    # Check if module is already installed
    if [ -f "$MODULES_DIR/third/$module_name.so" ]; then
        print_warning "Module '$module_name' is already installed"
        return 0
    fi

    # Try to install via module manager
    print_status "Installing via module manager..."
    if "$UNREALIRCD_BIN" module install "third/$module_name"; then
        print_success "Module '$module_name' installed successfully"

        # Check if we need to add loadmodule to config
        if [ -f "$CONFIG_DIR/unrealircd.conf" ]; then
            print_status "Checking if loadmodule line needs to be added..."
            if ! grep -q "loadmodule.*$module_name" "$CONFIG_DIR/unrealircd.conf"; then
                print_warning "You may need to add 'loadmodule \"third/$module_name\";' to your unrealircd.conf"
                print_warning "Then REHASH or restart UnrealIRCd"
            fi
        fi

        return 0
    fi

    # Fallback to manual installation
    print_warning "Module manager failed, attempting manual installation..."

    if [ ! -d "$CONTRIB_DIR/$module_name" ]; then
        print_error "Module '$module_name' not found in contrib directory"
        return 1
    fi

    cd "$CONTRIB_DIR/$module_name" || exit 1

    if [ -f "Makefile" ]; then
        print_status "Compiling module..."
        make clean 2>/dev/null || true
        make

        if [ -f "$module_name.so" ]; then
            print_status "Installing module..."
            cp "$module_name.so" "$MODULES_DIR/third/"
            print_success "Module '$module_name' installed manually"

            print_warning "You need to add 'loadmodule \"third/$module_name\";' to your unrealircd.conf"
            print_warning "Then REHASH or restart UnrealIRCd"
        else
            print_error "Module compilation failed"
            return 1
        fi
    else
        print_error "No Makefile found for module '$module_name'"
        return 1
    fi
}

# Uninstall a module
uninstall_module() {
    local module_name="$1"

    if [ -z "$module_name" ]; then
        print_error "Module name required"
        print_error "Usage: $0 uninstall <module-name>"
        return 1
    fi

    print_header "Uninstalling Module: $module_name"

    cd "$UNREALIRCD_DIR" || exit 1

    # Try to uninstall via module manager first
    if "$UNREALIRCD_BIN" module uninstall "third/$module_name" 2>/dev/null; then
        print_success "Module '$module_name' uninstalled successfully"
        return 0
    fi

    # Fallback to manual removal
    print_warning "Module manager failed, attempting manual removal..."

    if [ -f "$MODULES_DIR/third/$module_name.so" ]; then
        rm -f "$MODULES_DIR/third/$module_name.so"
        print_success "Module '$module_name' removed manually"

        print_warning "You should remove 'loadmodule \"third/$module_name\";' from your unrealircd.conf"
        print_warning "Then REHASH or restart UnrealIRCd"
    else
        print_error "Module '$module_name' not found in modules directory"
        return 1
    fi
}

# Upgrade modules
upgrade_modules() {
    local module_name="$1"

    print_header "Upgrading Modules"

    cd "$UNREALIRCD_DIR" || exit 1

    if [ -n "$module_name" ]; then
        print_status "Upgrading specific module: $module_name"
        if "$UNREALIRCD_BIN" module upgrade "third/$module_name" 2>/dev/null; then
            print_success "Module '$module_name' upgraded successfully"
        else
            print_error "Failed to upgrade module '$module_name'"
            return 1
        fi
    else
        print_status "Upgrading all modules..."
        if "$UNREALIRCD_BIN" module upgrade 2>/dev/null; then
            print_success "All modules upgraded successfully"
        else
            print_error "Failed to upgrade modules"
            return 1
        fi
    fi

    print_warning "After upgrading, you may need to REHASH or restart UnrealIRCd"
}

# Update contrib repository
update_contrib() {
    print_header "Updating Contrib Repository"

    if [ ! -d "$CONTRIB_DIR" ]; then
        print_error "Contrib directory not found: $CONTRIB_DIR"
        return 1
    fi

    cd "$CONTRIB_DIR" || exit 1

    print_status "Pulling latest changes from unrealircd-contrib..."
    if git pull --quiet origin main; then
        print_success "Contrib repository updated successfully"
        print_status "New modules may now be available"
    else
        print_error "Failed to update contrib repository"
        return 1
    fi
}

# Show installed modules
show_installed() {
    print_header "Installed Modules"

    if [ ! -d "$MODULES_DIR/third" ]; then
        print_status "No third-party modules installed"
        return 0
    fi

    cd "$MODULES_DIR/third" || exit 1

    local count=0
    for module in *.so; do
        if [ -f "$module" ]; then
            echo "  - ${module%.so}"
            ((count++))
        fi
    done

    if [ $count -eq 0 ]; then
        print_status "No third-party modules installed"
    else
        print_status "Total installed modules: $count"
    fi
}

# Show usage
show_usage() {
    cat <<EOF
UnrealIRCd Contrib Modules Management Script

Usage: $0 <command> [options]

Commands:
  list                    List all available contrib modules
  info <module>          Show detailed information about a module
  install <module>       Install a contrib module
  uninstall <module>     Uninstall a contrib module
  upgrade [module]       Upgrade all modules or a specific module
  update                 Update the contrib repository
  installed              Show currently installed modules
  help                   Show this help message

Examples:
  $0 list                    # List all available modules
  $0 info webpanel          # Show info about webpanel module
  $0 install webpanel       # Install webpanel module
  $0 uninstall webpanel     # Remove webpanel module
  $0 upgrade                # Upgrade all modules
  $0 upgrade webpanel       # Upgrade specific module
  $0 update                 # Update contrib repository
  $0 installed              # Show installed modules

Environment Variables:
  UNREALIRCD_DIR: UnrealIRCd installation directory (default: /usr/local/unrealircd)
  CONTRIB_DIR: Contrib modules directory (default: /usr/local/unrealircd/contrib)
  MODULES_DIR: Installed modules directory (default: /usr/local/unrealircd/modules)

Notes:
  - Some operations may require UnrealIRCd to be restarted
  - After installing modules, add 'loadmodule "third/modulename";' to unrealircd.conf
  - Use REHASH command in IRC or restart UnrealIRCd after configuration changes
  - Contrib modules are not officially supported by the UnrealIRCd team

EOF
}

# Main execution
main() {
    check_user

    case "${1:-help}" in
    list)
        list_modules
        ;;
    info)
        show_module_info "$2"
        ;;
    install)
        install_module "$2"
        ;;
    uninstall)
        uninstall_module "$2"
        ;;
    upgrade)
        upgrade_modules "$2"
        ;;
    update)
        update_contrib
        ;;
    installed)
        show_installed
        ;;
    help | --help | -h)
        show_usage
        ;;
    *)
        print_error "Unknown command: $1"
        echo
        show_usage
        exit 1
        ;;
    esac
}

# Run main function with all arguments
main "$@"
