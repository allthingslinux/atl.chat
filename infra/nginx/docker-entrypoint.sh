#!/bin/sh
set -e
# Render Prosody HTTPS proxy config from template
export CERT_DIR="${CERT_DIR:-/etc/nginx/certs}"
export XMPP_DOMAIN="${XMPP_DOMAIN:-xmpp.localhost}"
rm -f /etc/nginx/conf.d/default.conf
envsubst '${XMPP_DOMAIN} ${CERT_DIR}' < /etc/nginx/templates/prosody-https.conf.template > /etc/nginx/conf.d/prosody-https.conf
exec nginx -g "daemon off;"
