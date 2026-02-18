#!/bin/sh
set -e

# Configuration - domains from env (e.g. IRC_ROOT_DOMAIN=atl.chat or SSL_DOMAIN=example.com)
ROOT_DOMAIN=${IRC_ROOT_DOMAIN:-${SSL_DOMAIN:-atl.chat}}
WILDCARD_DOMAIN="*.$ROOT_DOMAIN"
EMAIL=${LETSENCRYPT_EMAIL:-admin@allthingslinux.org}
DATA_DIR="/data"

# Validate domain format (alphanumeric, hyphens, dots only - prevent injection)
case "$ROOT_DOMAIN" in
    *[!a-zA-Z0-9.-]*)
        echo "ERROR: Invalid domain format (contains disallowed characters): $ROOT_DOMAIN"
        exit 1
        ;;
    "")
        echo "ERROR: Domain cannot be empty"
        exit 1
        ;;
esac

# Validate email format (basic check - no spaces or shell metacharacters)
case "$EMAIL" in
    *[!a-zA-Z0-9@._+-]*)
        echo "ERROR: Invalid email format (contains disallowed characters): $EMAIL"
        exit 1
        ;;
    "")
        echo "ERROR: Email cannot be empty"
        exit 1
        ;;
esac

# Lego outputs: certificates/_.<domain>.crt and _.<domain>.key for wildcards
echo "Starting Cert Manager..."
echo "Domains: $WILDCARD_DOMAIN $ROOT_DOMAIN"
echo "Email: $EMAIL"

# Ensure we have credentials
if [ -z "$CLOUDFLARE_DNS_API_TOKEN" ]; then
    echo "Warning: CLOUDFLARE_DNS_API_TOKEN is not set. Certificate generation skipped."
    echo "To enable Let's Encrypt, set CLOUDFLARE_DNS_API_TOKEN in your .env file."
    exec sleep infinity
fi

# Initial issuance
echo "Requesting initial certificates..."
lego --email "$EMAIL" --dns cloudflare --domains "$WILDCARD_DOMAIN" --domains "$ROOT_DOMAIN" --path "$DATA_DIR" --accept-tos run

# Renewal loop
while true; do
    echo "Sleeping for 24 hours..."
    sleep 86400
    echo "Checking for renewal..."
    lego --email "$EMAIL" --dns cloudflare --domains "$WILDCARD_DOMAIN" --domains "$ROOT_DOMAIN" --path "$DATA_DIR" --accept-tos renew
done
