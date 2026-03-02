FROM nginx:1.27-alpine

LABEL org.opencontainers.image.source="https://github.com/allthingslinux/atl.chat" \
    org.opencontainers.image.description="Nginx HTTPS proxy for Prosody XMPP" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.vendor="All Things Linux" \
    org.opencontainers.image.title="atl-prosody-nginx"

RUN apk add --no-cache wget
COPY prosody-https.conf.template /etc/nginx/templates/
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
