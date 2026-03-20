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

# ObsidianIRC (web IRC client)
mod obsidianirc './apps/obsidianirc'

set export := true



# Initialize project: create data/ dirs, generate config, dev certs
# Run before first docker compose up. data/ is gitignored.
[group('Orchestration')]
init:
    @echo "Initializing project (data dirs, config, dev certs)..."
    ./scripts/init.sh dev

# Spin up the local development stack
[group('Orchestration')]
dev:
    @if docker compose -f compose.yaml -f compose.dev-override.yaml --env-file .env --env-file .env.dev ps --services --status running | rg -q "."; then \
        echo "Error: atl.chat containers are already running."; \
        echo "Run 'just down' (and/or 'just down-prod') before running 'just dev' again."; \
        echo "Running services:"; \
        docker compose -f compose.yaml -f compose.dev-override.yaml --env-file .env --env-file .env.dev ps --services --status running | sed 's/^/  - /'; \
        exit 1; \
    fi
    @echo "Initializing Development Environment..."
    ./scripts/init.sh dev
    docker compose -f compose.yaml -f compose.dev-override.yaml --env-file .env --env-file .env.dev --profile dev up -d

# Spin up the production stack
[group('Orchestration')]
prod:
    @echo "Initializing Production Environment..."
    ./scripts/init.sh prod
    docker compose -f compose.yaml -f compose.prod-override.yaml --env-file .env --env-file .env.prod up -d

# Stop all services
[group('Orchestration')]
down:
    docker compose --profile dev down

# Stop production services
[group('Orchestration')]
down-prod:
    docker compose -f compose.yaml -f compose.prod-override.yaml --env-file .env --env-file .env.prod down

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

# Generate a non-expiring Prosody admin API token (mod_http_admin_api Bearer auth)
# Prints the token to stdout. Pipe to your portal .env as PROSODY_REST_TOKEN=<token>
[group('Maintenance')]
prosody-token:
    @docker exec -i atl-xmpp-server prosodyctl shell <<< '>local tk = prosody.hosts["xmpp.localhost"].modules.tokenauth; local grant = tk.create_grant("admin@xmpp.localhost", "admin@xmpp.localhost", nil, {}); local token = tk.create_token("admin@xmpp.localhost", grant, "prosody:operator", nil, "portal-api"); print(token)' 2>&1 | grep -oP 'secret-token:\S+'

# Clean up unused Docker resources
[group('Maintenance')]
docker-system-clean:
    docker system prune -f
    docker volume prune -f
