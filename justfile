default:
    @just --list

# XMPP Service (Prosody)
mod xmpp './apps/xmpp'

# IRC Service (UnrealIRCd)
mod irc './apps/irc'

# Web Application (Next.js)
mod web './apps/web'

set export := true



# Spin up the local development stack
[group('Orchestration')]
dev:
    export PROSODY_DOMAIN="xmpp.localhost"
    export PROSODY_UPLOAD_EXTERNAL_URL="http://xmpp.localhost:5280/upload/"
    export PROSODY_PROXY_ADDRESS="xmpp.localhost"
    export PROSODY_SSL_KEY="certs/live/xmpp.localhost/privkey.pem"
    export PROSODY_SSL_CERT="certs/live/xmpp.localhost/fullchain.pem"
    export IRC_DOMAIN="irc.localhost"
    export IRC_SSL_CERT_PATH="/home/unrealircd/unrealircd/config/tls/live/irc.localhost/fullchain.pem"
    export IRC_SSL_KEY_PATH="/home/unrealircd/unrealircd/config/tls/live/irc.localhost/privkey.pem"
    @echo "Running IRC initialization..."
    @./apps/irc/scripts/init.sh
    docker compose --profile dev up -d

# Spin up the staging stack
[group('Orchestration')]
staging:
    docker compose --profile staging up -d

# Spin up the production stack (default profile)
[group('Orchestration')]
prod:
    docker compose --profile prod up -d

# Stop all services
[group('Orchestration')]
down:
    docker compose --profile dev down

# Stop all services
[group('Orchestration')]
down-staging:
    docker compose --profile staging down

# Stop all services
[group('Orchestration')]
down-prod:
    docker compose --profile prod down

# View logs (follow)
[group('Orchestration')]
logs service="":
    docker compose logs -f ${service:+"$service"}

# Show status of all services
[group('Orchestration')]
status:
    docker compose ps

# Run all linters via lefthook
[group('Verification')]
lint:
    lefthook run pre-commit

# Run security scans (Gitleaks, Trivy)
[group('Verification')]
scan:
    @echo "Running security scans..."
    # Placeholder for actual scan commands
    just --groups Verification

# Clean up unused Docker resources
[group('Maintenance')]
clean:
    docker system prune -f
    docker volume prune -f
