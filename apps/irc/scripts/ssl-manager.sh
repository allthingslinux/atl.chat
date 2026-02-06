#!/bin/bash
# shellcheck shell=bash

# ============================================================================
# SIMPLE SSL CERTIFICATE MANAGER
# ============================================================================
# Just the essentials - automatic renewal, monitoring, and service restart
# ============================================================================

set -euo pipefail

# Get script directory, app root, and repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS_IRC_ROOT="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$(dirname "$APPS_IRC_ROOT")")"

# Parse command line arguments for debug mode
DEBUG=false
VERBOSE=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --debug | -d)
      DEBUG=true
      VERBOSE=true
      shift
      ;;
    --verbose | -v)
      VERBOSE=true
      shift
      ;;
    *)
      break
      ;;
  esac
done

# Load environment variables from .env if it exists
if [ -f "$REPO_ROOT/.env" ]; then
  echo "[$(date)] SSL: Loading environment variables from .env"
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env"
else
  echo "[$(date)] SSL ERROR: .env file not found at $REPO_ROOT/.env" >&2
  echo "[$(date)] SSL ERROR: Please create .env file with required variables" >&2
  exit 1
fi

# Input validation
validate_configuration() {
  local errors=()

  if [[ -z ${IRC_ROOT_DOMAIN:-} ]]; then
    errors+=("IRC_ROOT_DOMAIN is not set in .env file")
  elif [[ ! $IRC_ROOT_DOMAIN =~ ^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
    errors+=("IRC_ROOT_DOMAIN '$IRC_ROOT_DOMAIN' is not a valid domain format")
  fi

  if [[ -z ${LETSENCRYPT_EMAIL:-} ]]; then
    errors+=("LETSENCRYPT_EMAIL is not set in .env file")
  elif [[ ! $LETSENCRYPT_EMAIL =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
    errors+=("LETSENCRYPT_EMAIL '$LETSENCRYPT_EMAIL' is not a valid email format")
  fi

  if [[ ${#errors[@]} -gt 0 ]]; then
    echo "[$(date)] SSL ERROR: Configuration validation failed:" >&2
    for error in "${errors[@]}"; do
      echo "[$(date)] SSL ERROR:   - $error" >&2
    done
    exit 1
  fi

  if $VERBOSE; then
    echo "[$(date)] SSL: Configuration validated successfully:"
    echo "[$(date)] SSL:   - Domain: $IRC_ROOT_DOMAIN"
    echo "[$(date)] SSL:   - Email: $LETSENCRYPT_EMAIL"
    echo "[$(date)] SSL:   - TLS Directory: $TLS_DIR"
    echo "[$(date)] SSL:   - Let's Encrypt Directory: $LETSENCRYPT_DIR"
    echo "[$(date)] SSL:   - Credentials File: $CREDENTIALS_FILE"
  fi
}

# Simple configuration
DOMAIN="${IRC_ROOT_DOMAIN}"
EMAIL="${LETSENCRYPT_EMAIL}"
TLS_DIR="$APPS_IRC_ROOT/services/unrealircd/config/tls"
LETSENCRYPT_DIR="$REPO_ROOT/data/letsencrypt"
CREDENTIALS_FILE="$APPS_IRC_ROOT/services/unrealircd/cloudflare-credentials.ini"

# Validate configuration early
validate_configuration

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
  echo -e "${GREEN}[$(date)] SSL: $1${NC}"
}

log_warn() {
  echo -e "${YELLOW}[$(date)] SSL WARNING: $1${NC}"
}

log_error() {
  echo -e "${RED}[$(date)] SSL ERROR: $1${NC}" >&2
}

log_debug() {
  if $DEBUG; then
    echo -e "${BLUE}[$(date)] SSL DEBUG: $1${NC}"
  fi
}

log_verbose() {
  if $VERBOSE; then
    echo -e "${BLUE}[$(date)] SSL VERBOSE: $1${NC}"
  fi
}

# Check if certificates exist and are valid
check_certificates() {
  local cert_file="$TLS_DIR/server.cert.pem"

  log_debug "Checking certificate at: $cert_file"

  if [[ ! -f $cert_file ]]; then
    log_warn "No SSL certificate found at $cert_file"
    log_debug "Certificate file does not exist"
    return 1
  fi

  # Check file permissions and readability
  if [[ ! -r $cert_file ]]; then
    log_error "Certificate file is not readable: $cert_file"
    log_error "Check file permissions (should be readable by current user)"
    return 1
  fi

  log_verbose "Certificate file exists and is readable"

  # Check expiry with better error handling
  local expiry_date
  local openssl_output

  log_debug "Running openssl to check certificate expiry"

  if ! openssl_output=$(openssl x509 -in "$cert_file" -noout -enddate 2>&1); then
    log_error "Failed to read certificate file with openssl"
    log_error "Openssl output: $openssl_output"
    log_error "Certificate file may be corrupted or have incorrect format"
    return 1
  fi

  # Extract expiry date
  if ! expiry_date=$(echo "$openssl_output" | grep "notAfter=" | cut -d= -f2); then
    log_error "Could not extract expiry date from certificate"
    log_error "Openssl output: $openssl_output"
    return 1
  fi

  log_verbose "Certificate expiry date: $expiry_date"

  # Parse expiry timestamp with better error handling
  local expiry_timestamp
  local current_timestamp
  local date_output

  if ! date_output=$(date -d "$expiry_date" +%s 2>&1); then
    log_error "Failed to parse certificate expiry date: $expiry_date"
    log_error "Date command output: $date_output"
    log_error "This may be due to locale settings or invalid date format"
    return 1
  fi

  expiry_timestamp="$date_output"
  current_timestamp=$(date +%s)
  days_until_expiry=$(((expiry_timestamp - current_timestamp) / 86400))

  log_verbose "Days until expiry: $days_until_expiry"

  if [[ $days_until_expiry -le 0 ]]; then
    log_error "Certificate expired $((-days_until_expiry)) days ago (on $expiry_date)"
    return 1
  elif [[ $days_until_expiry -le 7 ]]; then
    log_warn "Certificate expires in $days_until_expiry days (on $expiry_date) - renewal needed"
    return 1
  elif [[ $days_until_expiry -le 30 ]]; then
    log_warn "Certificate expires in $days_until_expiry days (on $expiry_date)"
    return 0
  else
    log_info "Certificate is valid for $days_until_expiry more days (expires $expiry_date)"
    return 0
  fi
}

# Issue new certificates
issue_certificates() {
  log_info "Issuing new SSL certificates for $DOMAIN..."
  log_debug "Using email: $EMAIL"
  log_debug "Let's Encrypt directory: $LETSENCRYPT_DIR"
  log_debug "Credentials file: $CREDENTIALS_FILE"

  # Check if credentials exist and are readable
  if [[ ! -f $CREDENTIALS_FILE ]]; then
    log_error "Cloudflare credentials not found at $CREDENTIALS_FILE"
    log_error "Please create cloudflare-credentials.ini with your API token"
    log_error "Expected format:"
    log_error "  dns_cloudflare_api_token = YOUR_TOKEN_HERE"
    return 1
  fi

  if [[ ! -r $CREDENTIALS_FILE ]]; then
    log_error "Cloudflare credentials file is not readable: $CREDENTIALS_FILE"
    log_error "Check file permissions"
    return 1
  fi

  log_verbose "Credentials file exists and is readable"

  # Validate credentials file format
  if ! grep -q "^dns_cloudflare_api_token.*=" "$CREDENTIALS_FILE"; then
    log_error "Invalid Cloudflare credentials file format"
    log_error "File should contain: dns_cloudflare_api_token = YOUR_TOKEN"
    return 1
  fi

  log_verbose "Credentials file format appears valid"

  # Create Let's Encrypt directory if it doesn't exist
  if [[ ! -d $LETSENCRYPT_DIR ]]; then
    log_verbose "Creating Let's Encrypt directory: $LETSENCRYPT_DIR"
    if ! mkdir -p "$LETSENCRYPT_DIR"; then
      log_error "Failed to create Let's Encrypt directory: $LETSENCRYPT_DIR"
      return 1
    fi
  fi

  # Check Docker availability
  if ! command -v docker > /dev/null 2>&1; then
    log_error "Docker command not found"
    log_error "Please ensure Docker is installed and available in PATH"
    return 1
  fi

  log_verbose "Docker is available"

  # Fix Let's Encrypt permissions after Docker operations
  fix_letsencrypt_permissions

  # Build the certbot command
  local certbot_cmd=(
    docker run --rm
    -v "$LETSENCRYPT_DIR:/etc/letsencrypt"
    -v "$CREDENTIALS_FILE:/etc/letsencrypt/cloudflare-credentials.ini:ro"
    certbot/dns-cloudflare:latest
    certonly
    --dns-cloudflare
    --dns-cloudflare-credentials=/etc/letsencrypt/cloudflare-credentials.ini
    --email "$EMAIL"
    --agree-tos
    --no-eff-email
    -d "$DOMAIN"
    -d "*.$DOMAIN"
  )

  log_debug "Running certbot command:"
  log_debug "  ${certbot_cmd[*]}"

  # Run certbot with error capture
  local certbot_output
  local certbot_exit_code

  if certbot_output=$("${certbot_cmd[@]}" 2>&1); then
    log_info "Certificates issued successfully"
    log_verbose "Certbot output: $certbot_output"

    # Fix permissions after Docker operations
    fix_letsencrypt_permissions

    copy_certificates
    return 0
  else
    certbot_exit_code=$?
    log_error "Failed to issue certificates (exit code: $certbot_exit_code)"
    log_error "Certbot output:"
    echo "$certbot_output" | while IFS= read -r line; do
      log_error "  $line"
    done

    # Provide specific troubleshooting based on common errors
    if echo "$certbot_output" | grep -qi "cloudflare"; then
      log_error "This appears to be a Cloudflare API issue:"
      log_error "  - Check your API token is valid and has correct permissions"
      log_error "  - Verify the token format in credentials file"
      log_error "  - Ensure DNS records exist for $DOMAIN and *.$DOMAIN"
    elif echo "$certbot_output" | grep -qi "dns"; then
      log_error "This appears to be a DNS issue:"
      log_error "  - Check that $DOMAIN and *.$DOMAIN resolve correctly"
      log_error "  - Verify DNS propagation (may take up to 24 hours)"
    fi

    return 1
  fi
}

# Renew existing certificates
renew_certificates() {
  log_info "Checking for certificate renewal..."

  if ! check_certificates; then
    log_info "Certificates need renewal - attempting renewal..."
    log_debug "Starting certificate renewal process"

    # Check if credentials exist before attempting renewal
    if [[ ! -f $CREDENTIALS_FILE ]]; then
      log_error "Cloudflare credentials not found at $CREDENTIALS_FILE"
      log_error "Cannot renew certificates without credentials"
      return 1
    fi

    # Build the renewal command
    local renew_cmd=(
      docker run --rm
      -v "$LETSENCRYPT_DIR:/etc/letsencrypt"
      -v "$CREDENTIALS_FILE:/etc/letsencrypt/cloudflare-credentials.ini:ro"
      certbot/dns-cloudflare:latest
      renew
      --dns-cloudflare
      --dns-cloudflare-credentials=/etc/letsencrypt/cloudflare-credentials.ini
      --no-random-sleep-on-renew
    )

    # Add quiet flag unless in verbose mode
    if ! $VERBOSE; then
      renew_cmd+=(--quiet)
    fi

    log_debug "Running renewal command:"
    log_debug "  ${renew_cmd[*]}"

    # Fix Let's Encrypt permissions before renewal
    fix_letsencrypt_permissions

    # Run renewal with error capture
    local renew_output
    local renew_exit_code

    if renew_output=$("${renew_cmd[@]}" 2>&1); then
      log_info "Certificates renewed successfully"
      if $VERBOSE; then
        log_verbose "Renewal output: $renew_output"
      fi

      # Fix permissions after Docker operations
      fix_letsencrypt_permissions

      copy_certificates
      restart_services
      return 0
    else
      renew_exit_code=$?
      log_error "Certificate renewal failed (exit code: $renew_exit_code)"
      if $VERBOSE; then
        log_error "Renewal output:"
        echo "$renew_output" | while IFS= read -r line; do
          log_error "  $line"
        done
      else
        log_error "Run with --verbose flag to see detailed renewal output"
      fi

      # Provide troubleshooting for renewal failures
      if echo "$renew_output" | grep -qi "cloudflare"; then
        log_error "This appears to be a Cloudflare API issue during renewal"
      elif echo "$renew_output" | grep -qi "challenge"; then
        log_error "This appears to be a DNS challenge issue during renewal"
      fi

      return 1
    fi
  else
    log_info "Certificates are still valid - no renewal needed"
    return 0
  fi
}

# Fix Let's Encrypt directory permissions
# This is needed because Docker creates files with different ownership
fix_letsencrypt_permissions() {
  log_debug "Fixing Let's Encrypt directory permissions..."

  # Check if Let's Encrypt directory exists
  if [[ ! -d $LETSENCRYPT_DIR ]]; then
    log_verbose "Let's Encrypt directory doesn't exist yet, skipping permission fix"
    return 0
  fi

  # Get current user and group
  local current_user current_group
  current_user=$(id -u)
  current_group=$(id -g)

  log_debug "Setting ownership to user $current_user, group $current_group"

  # Fix ownership recursively
  if ! chown -R "$current_user:$current_group" "$LETSENCRYPT_DIR" 2> /dev/null; then
    log_verbose "Permission fix attempted (may require sudo for existing files)"

    # Try with sudo if available
    if command -v sudo > /dev/null 2>&1; then
      log_debug "Attempting permission fix with sudo..."
      if sudo chown -R "$current_user:$current_group" "$LETSENCRYPT_DIR" 2> /dev/null; then
        log_verbose "Permission fix successful with sudo"
      else
        log_warn "Could not fix permissions with sudo - some operations may fail"
        log_warn "You may need to manually run: sudo chown -R \$(id -u):\$(id -g) $LETSENCRYPT_DIR"
      fi
    else
      log_warn "Could not fix permissions - sudo not available"
      log_warn "You may need to manually run: sudo chown -R \$(id -u):\$(id -g) $LETSENCRYPT_DIR"
    fi
  else
    log_verbose "Permission fix successful"
  fi

  # Ensure proper directory permissions
  if [[ -d $LETSENCRYPT_DIR ]]; then
    chmod 755 "$LETSENCRYPT_DIR" 2> /dev/null || true
    if [[ -d "$LETSENCRYPT_DIR/live" ]]; then
      chmod 755 "$LETSENCRYPT_DIR/live" 2> /dev/null || true
    fi
    if [[ -d "$LETSENCRYPT_DIR/archive" ]]; then
      chmod 755 "$LETSENCRYPT_DIR/archive" 2> /dev/null || true
    fi
  fi
}

# Copy certificates to UnrealIRCd
copy_certificates() {
  log_info "Copying certificates to UnrealIRCd..."
  log_debug "Source directory: $LETSENCRYPT_DIR/live/$DOMAIN"
  log_debug "Target directory: $TLS_DIR"

  # Fix permissions before attempting to copy
  fix_letsencrypt_permissions

  # Check if source certificates exist
  local cert_source="$LETSENCRYPT_DIR/live/$DOMAIN/fullchain.pem"
  local key_source="$LETSENCRYPT_DIR/live/$DOMAIN/privkey.pem"

  if [[ ! -f $cert_source ]]; then
    log_error "Certificate file not found: $cert_source"
    log_error "Certificate issuance may have failed"
    return 1
  fi

  if [[ ! -f $key_source ]]; then
    log_error "Private key file not found: $key_source"
    log_error "Certificate issuance may have failed"
    return 1
  fi

  log_verbose "Source certificate files found"

  # Create target directory if it doesn't exist
  if [[ ! -d $TLS_DIR ]]; then
    log_verbose "Creating TLS directory: $TLS_DIR"
    if ! mkdir -p "$TLS_DIR"; then
      log_error "Failed to create TLS directory: $TLS_DIR"
      return 1
    fi
  fi

  # Ensure CA certificate bundle exists (required for SSL validation)
  local ca_bundle_target="$TLS_DIR/curl-ca-bundle.crt"
  local ca_bundle_source="$REPO_ROOT/apps/irc/services/unrealircd/config/examples/tls/curl-ca-bundle.crt"

  if [[ ! -f $ca_bundle_target ]]; then
    log_verbose "CA certificate bundle not found, restoring from template..."
    if [[ -f $ca_bundle_source ]]; then
      if ! cp "$ca_bundle_source" "$ca_bundle_target"; then
        log_error "Failed to copy CA certificate bundle"
        return 1
      fi
      log_verbose "CA certificate bundle restored successfully"
    else
      log_warn "CA certificate bundle template not found at $ca_bundle_source"
      log_warn "SSL certificate validation may not work properly"
    fi
  fi

  # Copy certificates with error handling
  local cert_target="$TLS_DIR/server.cert.pem"
  local key_target="$TLS_DIR/server.key.pem"

  log_debug "Copying certificate to: $cert_target"
  if ! cp "$cert_source" "$cert_target"; then
    log_error "Failed to copy certificate file"
    return 1
  fi

  log_debug "Copying private key to: $key_target"
  if ! cp "$key_source" "$key_target"; then
    log_error "Failed to copy private key file"
    return 1
  fi

  # Set permissions with proper error handling
  log_debug "Setting certificate file permissions to 644"
  if ! chmod 644 "$cert_target"; then
    log_error "Failed to set permissions on certificate file: $cert_target"
    log_error "Certificate may not be readable by UnrealIRCd"
    return 1
  fi

  log_debug "Setting private key file permissions to 644"
  if ! chmod 644 "$key_target"; then
    log_error "Failed to set permissions on private key file: $key_target"
    log_error "Private key may not be readable by UnrealIRCd"
    return 1
  fi

  log_debug "Setting TLS directory permissions to 755"
  if ! chmod 755 "$TLS_DIR"; then
    log_error "Failed to set permissions on TLS directory: $TLS_DIR"
    return 1
  fi

  # Verify the copied files
  if [[ ! -f $cert_target ]] || [[ ! -f $key_target ]]; then
    log_error "Certificate files were not copied successfully"
    return 1
  fi

  # Verify file sizes are reasonable
  local cert_size key_size
  cert_size=$(stat -f%z "$cert_target" 2> /dev/null || stat -c%s "$cert_target" 2> /dev/null || echo "0")
  key_size=$(stat -f%z "$key_target" 2> /dev/null || stat -c%s "$key_target" 2> /dev/null || echo "0")

  if [[ $cert_size -lt 500 ]]; then
    log_warn "Certificate file seems unusually small ($cert_size bytes)"
    log_warn "This may indicate a problem with the certificate"
  fi

  # ECDSA keys are much smaller than RSA keys, so use lower threshold
  if [[ $key_size -lt 100 ]]; then
    log_warn "Private key file seems unusually small ($key_size bytes)"
    log_warn "This may indicate a problem with the private key"
  elif [[ $key_size -gt 100 && $key_size -lt 300 ]]; then
    log_verbose "Private key size ($key_size bytes) is typical for ECDSA keys"
  fi

  log_info "Certificates copied successfully"
  log_verbose "Certificate file: $cert_target ($cert_size bytes)"
  log_verbose "Private key file: $key_target ($key_size bytes)"
  return 0
}

# Restart services that use certificates
restart_services() {
  log_info "Restarting services that use certificates..."

  # Check if Docker is available and accessible
  if ! command -v docker > /dev/null 2>&1; then
    log_error "Docker command not found - cannot restart services"
    log_error "Please restart services manually:"
    log_error "  docker restart unrealircd unrealircd-webpanel"
    return 1
  fi

  # Check Docker socket access
  local docker_socket="/var/run/docker.sock"
  if [[ ! -S $docker_socket ]]; then
    log_error "Docker socket not found at $docker_socket"
    log_error "This may indicate Docker is not running or socket is in a different location"
    log_error "Please restart services manually:"
    log_error "  docker restart unrealircd unrealircd-webpanel"
    return 1
  fi

  if [[ ! -w $docker_socket ]]; then
    log_error "No write permission to Docker socket: $docker_socket"
    log_error "You may need to run this script as root or add yourself to the docker group"
    log_error "Please restart services manually:"
    log_error "  sudo docker restart unrealircd unrealircd-webpanel"
    return 1
  fi

  log_verbose "Docker socket is accessible"

  # Check if containers exist before trying to restart them
  local containers=("atl-irc-server" "atl-irc-webpanel")
  local restart_needed=()
  local restart_succeeded=()
  local restart_failed=()

  for container in "${containers[@]}"; do
    log_debug "Checking if container exists: $container"
    if docker ps -a --format "table {{.Names}}" | grep -q "^${container}$"; then
      log_verbose "Container $container exists"
      restart_needed+=("$container")
    else
      log_warn "Container $container does not exist - skipping restart"
    fi
  done

  if [[ ${#restart_needed[@]} -eq 0 ]]; then
    log_warn "No containers found that need restarting"
    return 0
  fi

  log_info "Restarting containers: ${restart_needed[*]}"

  # Restart containers with error handling
  for container in "${restart_needed[@]}"; do
    log_debug "Restarting container: $container"
    if docker restart "$container" > /dev/null 2>&1; then
      log_info "Container $container restarted successfully"
      restart_succeeded+=("$container")
    else
      local restart_exit_code=$?
      log_error "Failed to restart container $container (exit code: $restart_exit_code)"
      restart_failed+=("$container")
    fi
  done

  # Report results
  if [[ ${#restart_succeeded[@]} -gt 0 ]]; then
    log_info "Successfully restarted: ${restart_succeeded[*]}"
  fi

  if [[ ${#restart_failed[@]} -gt 0 ]]; then
    log_error "Failed to restart: ${restart_failed[*]}"
    log_error "You may need to restart these containers manually"
    return 1
  fi

  log_info "All certificate-dependent services restarted successfully"
  return 0
}

# Display help information
show_help() {
  cat << EOF
SSL Certificate Manager for IRC Infrastructure

USAGE:
    $0 [OPTIONS] [COMMAND]

COMMANDS:
    check       Check certificate validity and expiry
    issue       Issue new SSL certificates
    renew       Renew existing certificates if needed
    copy        Copy certificates to UnrealIRCd directory
    restart     Restart services that use certificates

OPTIONS:
    -d, --debug     Enable debug logging (most verbose)
    -v, --verbose   Enable verbose logging
    -h, --help      Show this help message

EXAMPLES:
    $0 check                    # Check certificate status
    $0 --verbose issue          # Issue certificates with verbose output
    $0 --debug renew            # Renew certificates with debug output

ENVIRONMENT VARIABLES (from .env file):
    IRC_ROOT_DOMAIN    - Domain for SSL certificates (e.g., atl.dev)
    LETSENCRYPT_EMAIL  - Email for Let's Encrypt notifications

FILES:
    ./cloudflare-credentials.ini           - Cloudflare API token
    $REPO_ROOT/data/letsencrypt/           - Let's Encrypt data directory
    $APPS_IRC_ROOT/services/unrealircd/config/tls/ - UnrealIRCd TLS certificates

For more information, see the SSL documentation.
EOF
}

# Main command handler
main() {
  local command="check"

  # Parse remaining arguments as command if not already consumed
  while [[ $# -gt 0 ]]; do
    case $1 in
      check | issue | renew | copy | restart)
        command="$1"
        shift
        break
        ;;
      -h | --help)
        show_help
        exit 0
        ;;
      *)
        log_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
    esac
  done

  log_debug "Starting SSL manager with command: $command"
  log_debug "Debug mode: $DEBUG"
  log_debug "Verbose mode: $VERBOSE"

  case "$command" in
    "check")
      if check_certificates; then
        echo "OK"
        exit 0
      else
        echo "NEEDS_RENEWAL"
        exit 1
      fi
      ;;
    "issue")
      if issue_certificates; then
        log_info "Certificate setup completed successfully"
        exit 0
      else
        log_error "Certificate setup failed"
        exit 1
      fi
      ;;
    "renew")
      if renew_certificates; then
        log_info "Certificate renewal completed successfully"
        exit 0
      else
        log_error "Certificate renewal failed"
        exit 1
      fi
      ;;
    "copy")
      if copy_certificates; then
        log_info "Certificate copy completed successfully"
        exit 0
      else
        log_error "Certificate copy failed"
        exit 1
      fi
      ;;
    "restart")
      if restart_services; then
        log_info "Service restart completed successfully"
        exit 0
      else
        log_error "Service restart failed"
        exit 1
      fi
      ;;
    *)
      log_error "Unknown command: $command"
      show_help
      exit 1
      ;;
  esac
}

main "$@"
