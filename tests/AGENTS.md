# Root Test Suite

> Scope: Root `tests/` directory. Inherits [AGENTS.md](../AGENTS.md).

IRC, integration, e2e, and protocol tests. Run via `just test` or `uv run pytest tests/`.

## Structure

| Dir | Purpose |
|-----|---------|
| `unit/` | Configuration, Docker client, environment validation |
| `integration/` | IRC functionality, protocol, services, infrastructure |
| `e2e/` | End-to-end workflow tests |
| `protocol/` | IRC message protocol tests |
| `legacy/` | Deprecated integration tests (kept for reference) |
| `controllers/` | IRC server controller classes |
| `fixtures/` | Test fixtures and sample data |
| `utils/` | Test helpers, base cases, IRC test client |

## Commands

- `just test` — run all root tests
- `just irc test` — same (from unrealircd mod)
- `uv run pytest tests/unit/` — unit only
- `uv run pytest tests/integration/` — integration only
- `uv run pytest -m docker` — Docker-related tests

## Related

- [Monorepo AGENTS.md](../AGENTS.md)
- [apps/bridge/tests/AGENTS.md](../apps/bridge/tests/AGENTS.md) — bridge-specific tests
