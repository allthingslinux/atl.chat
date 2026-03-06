#!/bin/sh
set -e

export FLUUX_DOMAIN="${FLUUX_DOMAIN:-webxmpp.localhost}"
export FLUUX_CERT_DOMAIN="${FLUUX_CERT_DOMAIN:-${FLUUX_DOMAIN}}"
export CERT_DIR="${CERT_DIR:-/etc/nginx/certs}"

rm -f /etc/nginx/conf.d/default.conf

CERT_FILE="${CERT_DIR}/live/${FLUUX_CERT_DOMAIN}/fullchain.pem"
KEY_FILE="${CERT_DIR}/live/${FLUUX_CERT_DOMAIN}/privkey.pem"

if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    echo "TLS certs found for ${FLUUX_CERT_DOMAIN} — enabling HTTPS"
    TEMPLATE="nginx-tls.conf.template"
else
    echo "No TLS certs found at ${CERT_FILE} — serving HTTP only (dev mode)"
    TEMPLATE="nginx-plain.conf.template"
fi

# shellcheck disable=SC2016
envsubst '${FLUUX_DOMAIN} ${FLUUX_CERT_DOMAIN} ${CERT_DIR}' \
    < "/etc/nginx/templates/${TEMPLATE}" \
    > /etc/nginx/conf.d/fluux.conf

exec nginx -g "daemon off;"
