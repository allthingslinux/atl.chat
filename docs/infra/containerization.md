# Containerization Standards

The `atl.chat` monorepo utilizes a standardized Docker-based orchestration model to ensure consistency across Local, Staging, and Production environments.

## Core Principles
1. **Standardized Naming**: All services use `compose.yaml` (orchestration) and `Containerfile` (build).
2. **Unified Hub**: The root [compose.yaml](../../compose.yaml) aggregates all service-level configurations using the `include` directive.
3. **Orchestration Tooling**: We use `just` as our primary command runner instead of Makefiles for better cross-platform support and monorepo awareness.

## Service Structure
Every application in `apps/` must follow this structure:
```
apps/<service>/
├── compose.yaml       # Service-specific orchestration
├── Containerfile      # Build instructions
└── .dockerignore      # Build context filtering
```

## Environment Management
- **Local Dev**: Handled via `compose.override.yaml` (automatically loaded).
- **Staging/Prod**: Managed via Docker Compose **profiles**.

## Common Commands
| Action | Command | Description |
|--------|---------|-------------|
| Start All | `just up` | Spins up the entire stack |
| Start Specific | `just profile=<name> up` | Spins up a specific profile (e.g., `irc`, `xmpp`) |
| Stop | `just down` | Shuts down and cleans up |
| Config Check | `just compose config` | Validates all included compose files |

## Networking
All containers connect to a shared internal network named `atl-network`. Inter-service communication should use Docker service names as hostnames.
