#!/bin/bash
set -e

# Configuration
DOMAINS="*.atl.chat atl.chat"
EMAIL=${LETSENCRYPT_EMAIL:-admin@allthingslinux.org}
DATA_DIR="/data"

echo "Starting Cert Manager..."
echo "Domains: $DOMAINS"
echo "Email: $EMAIL"

# Ensure we have credentials
if [ -z "$CLOUDFLARE_DNS_API_TOKEN" ]; then
    echo "Error: CLOUDFLARE_DNS_API_TOKEN is not set."
    exit 1
fi

# Initial issuance
echo "Requesting initial certificates..."
lego --email "$EMAIL" --dns cloudflare --domains "*.atl.chat" --domains "atl.chat" --path "$DATA_DIR" --accept-tos run

# Renewal loop
while true; do
    echo "Sleeping for 24 hours..."
    sleep 86400
    echo "Checking for renewal..."
    lego --email "$EMAIL" --dns cloudflare --domains "*.atl.chat" --domains "atl.chat" --path "$DATA_DIR" --accept-tos renew
done
