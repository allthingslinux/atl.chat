default:
    @just --list

# XMPP Service (Prosody)
mod xmpp './apps/xmpp'

# IRC Service (UnrealIRCd)
mod irc './apps/irc'

set export := true

# Spin up the entire stack (or specific profiles)
[group('Orchestration')]
up profile="":
    docker compose ${profile:+--profile "$profile"} up -d

# Spin up the local development stack with overrides
[group('Orchestration')]
dev profile="":
    docker compose ${profile:+--profile "$profile"} -f compose.yaml -f compose.override.yaml up -d

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
