default:
    @just --list

# XMPP Service (Prosody)
mod xmpp './apps/prosody'

# IRC Services (UnrealIRCd, Atheme, WebPanel)
mod irc './apps/unrealircd'

# Web Application (Next.js)
mod web './apps/web'

# Bridge (Discord↔IRC↔XMPP)
mod bridge './apps/bridge'

# The Lounge (web IRC client)
mod lounge './apps/thelounge'

set export := true



# Initialize project: create data/ dirs, generate config, dev certs
# Run before first docker compose up. data/ is gitignored.
[group('Orchestration')]
init:
    @echo "Initializing project (data dirs, config, dev certs)..."
    ./scripts/init.sh

# Spin up the local development stack
[group('Orchestration')]
dev:
    @echo "Initializing Development Environment..."
    @set -a && . ./.env.dev && set +a && \
     ./scripts/init.sh
    docker compose --env-file .env --env-file .env.dev --profile dev up -d

# Spin up the production stack
[group('Orchestration')]
prod:
    @echo "Initializing Production Environment..."
    export ATL_ENVIRONMENT=prod && ./scripts/init.sh
    docker compose --env-file .env up -d

# Stop all services
[group('Orchestration')]
down:
    docker compose --profile dev down

# Stop production services
[group('Orchestration')]
down-prod:
    docker compose -p atl-chat-prod down

# View logs (follow)
[group('Orchestration')]
logs service="":
    docker compose logs -f ${service:+"$service"}

# Show status of all services
[group('Orchestration')]
status:
    docker compose ps

# Run all linters via pre-commit
[group('Verification')]
lint:
    pre-commit run --all-files

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

# Run tests (atl.chat root tests)
[group('Build')]
test:
    uv run pytest tests/

# Run all tests (root + bridge)
[group('Build')]
test-all:
    uv run pytest tests/
    just bridge test

# Clean up unused Docker resources
[group('Maintenance')]
clean:
    docker system prune -f
    docker volume prune -f
