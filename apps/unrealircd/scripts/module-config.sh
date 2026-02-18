#!/bin/bash
# shellcheck shell=bash
# UnrealIRCd Module Configuration Helper
# Easily add/remove loadmodule lines from unrealircd.conf

set -euo pipefail

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Configuration
CONFIG_FILE="/home/unrealircd/unrealircd/config/unrealircd.conf"
BACKUP_SUFFIX=".backup.$(date +%Y%m%d_%H%M%S)"

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
    exit 1
  fi
}

# Check if config file exists
check_config() {
  if [ ! -f "$CONFIG_FILE" ]; then
    print_error "Configuration file not found: $CONFIG_FILE"
    exit 1
  fi
}

# Backup configuration file
backup_config() {
  local backup_file="${CONFIG_FILE}${BACKUP_SUFFIX}"
  cp "$CONFIG_FILE" "$backup_file"
  print_status "Configuration backed up to: $backup_file"
}

# Add a module to configuration
add_module() {
  local module_name="$1"

  if [ -z "$module_name" ]; then
    print_error "Module name required"
    print_error "Usage: $0 add <module-name>"
    exit 1
  fi

  print_header "Adding Module: $module_name"

  check_user
  check_config

  # Check if module is already loaded
  if grep -q "loadmodule.*$module_name" "$CONFIG_FILE"; then
    print_warning "Module '$module_name' is already loaded in configuration"
    return 0
  fi

  # Check if module file exists
  if [ ! -f "/home/unrealircd/unrealircd/modules/third/$module_name.so" ]; then
    print_warning "Module file not found: /home/unrealircd/unrealircd/modules/third/$module_name.so"
    print_warning "Make sure to install the module first using: manage-modules.sh install $module_name"
  fi

  # Backup configuration
  backup_config

  # Find a good place to add the loadmodule line (after other loadmodule lines)
  local temp_file
  temp_file=$(mktemp)

  # Look for the last loadmodule line and add after it
  if grep -q "loadmodule" "$CONFIG_FILE"; then
    # Add after the last loadmodule line
    awk '/loadmodule/ { print; last_loadmodule = NR }
             !/loadmodule/ {
                 if (last_loadmodule && NR == last_loadmodule + 1) {
                     print "loadmodule \"third/'"$module_name"'\";"
                 }
                 print
             }' "$CONFIG_FILE" > "$temp_file"
  else
    # No loadmodule lines found, add at the end
    cp "$CONFIG_FILE" "$temp_file"
    echo "" >> "$temp_file"
    echo "loadmodule \"third/$module_name\";" >> "$temp_file"
  fi

  # Replace original file
  mv "$temp_file" "$CONFIG_FILE"

  print_success "Module '$module_name' added to configuration"
  print_warning "Use REHASH command in IRC or restart UnrealIRCd to load the module"
}

# Remove a module from configuration
remove_module() {
  local module_name="$1"

  if [ -z "$module_name" ]; then
    print_error "Module name required"
    print_error "Usage: $0 remove <module-name>"
    exit 1
  fi

  print_header "Removing Module: $module_name"

  check_user
  check_config

  # Check if module is loaded in configuration
  if ! grep -q "loadmodule.*$module_name" "$CONFIG_FILE"; then
    print_warning "Module '$module_name' is not loaded in configuration"
    return 0
  fi

  # Backup configuration
  backup_config

  # Remove the loadmodule line
  local temp_file
  temp_file=$(mktemp)
  grep -v "loadmodule.*$module_name" "$CONFIG_FILE" > "$temp_file"

  # Replace original file
  mv "$temp_file" "$CONFIG_FILE"

  print_success "Module '$module_name' removed from configuration"
  print_warning "Use REHASH command in IRC or restart UnrealIRCd to unload the module"
}

# List loaded modules
list_loaded() {
  print_header "Loaded Modules in Configuration"

  check_user
  check_config

  local count=0
  while IFS= read -r line; do
    if [[ $line =~ loadmodule[[:space:]]+\"([^\"]+)\" ]]; then
      echo "  - ${BASH_REMATCH[1]}"
      ((count++))
    fi
  done < "$CONFIG_FILE"

  if [ $count -eq 0 ]; then
    print_status "No modules loaded in configuration"
  else
    print_status "Total loaded modules: $count"
  fi
}

# Show usage
show_usage() {
  cat << EOF
UnrealIRCd Module Configuration Helper

Usage: $0 <command> [options]

Commands:
  add <module>           Add a module to unrealircd.conf
  remove <module>        Remove a module from unrealircd.conf
  list                   List all loaded modules in configuration
  help                   Show this help message

Examples:
  $0 add webpanel           # Add webpanel module to config
  $0 remove webpanel        # Remove webpanel module from config
  $0 list                   # List all loaded modules
  $0 help                   # Show this help message

Notes:
  - This script modifies unrealircd.conf directly
  - A backup is automatically created before changes
  - After changes, use REHASH command in IRC or restart UnrealIRCd
  - Make sure modules are installed before adding them to config

EOF
}

# Main execution
main() {
  case "${1:-help}" in
    add)
      add_module "$2"
      ;;
    remove)
      remove_module "$2"
      ;;
    list)
      list_loaded
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
