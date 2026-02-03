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
    export PROSODY_DOMAIN="localhost"
    export PROSODY_UPLOAD_EXTERNAL_URL="http://localhost:5280/upload/"
    export PROSODY_PROXY_ADDRESS="localhost"
    export PROSODY_SSL_KEY="certs/live/localhost/privkey.pem"
    export PROSODY_SSL_CERT="certs/live/localhost/fullchain.pem"
    export IRC_DOMAIN="localhost"
    export IRC_SSL_CERT_PATH="/home/unrealircd/unrealircd/conf/tls/live/localhost/fullchain.pem"
    export IRC_SSL_KEY_PATH="/home/unrealircd/unrealircd/conf/tls/live/localhost/privkey.pem"
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
    docker compose down

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
