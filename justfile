default:
    @just --list

# XMPP Service (Prosody)
mod xmpp './apps/xmpp'

# IRC Service (UnrealIRCd)
mod irc './apps/irc'

# Web Application (Next.js)
mod web './apps/web'

set export := true



# Initialize project: create data/ dirs, generate config, dev certs
# Run before first docker compose up. data/ is gitignored.
[group('Orchestration')]
init:
    @echo "Initializing project (data dirs, config, dev certs)..."
    ./apps/irc/scripts/init.sh

# Spin up the local development stack
[group('Orchestration')]
dev:
    @echo "Initializing Development Environment..."
    @set -a && . ./.env.dev && set +a && \
     ./apps/irc/scripts/init.sh
    docker compose --env-file .env --env-file .env.dev --profile dev up -d

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

# Build all services (delegates to docker compose)
[group('Build')]
build:
    docker compose build

# Run tests (IRC pytest; add web/xmpp as needed)
[group('Build')]
test:
    just irc test

# Clean up unused Docker resources
[group('Maintenance')]
clean:
    docker system prune -f
    docker volume prune -f
