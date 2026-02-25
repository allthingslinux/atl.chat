FROM nginx:alpine
RUN apk add --no-cache wget
COPY prosody-https.conf.template /etc/nginx/templates/
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
