# Documentation

> Scope: `docs/` — inherits [AGENTS.md](../AGENTS.md).

Documentation hub for atl.chat. Human-readable guides; not code.

## Structure

| Dir | Purpose |
|-----|---------|
| `architecture/` | CI/CD, new-service guide, architecture overview |
| `bridges/` | Bridge infrastructure overview |
| `examples/` | Example configs (nginx, prometheus, unrealircd) |
| `infra/` | Containerization, data layout, networking, SSL |
| `onboarding/` | Local setup, just, pre-commit |
| `services/` | Per-service docs (irc, xmpp, web) |

## Key Files

- [README.md](README.md) — Hub index
- [architecture/new-service.md](architecture/new-service.md) — Adding new services
- [infra/data-structure.md](infra/data-structure.md) — Data layout
- [services/irc/README.md](services/irc/README.md) — IRC service docs

## Related

- [Monorepo AGENTS.md](../AGENTS.md)
- [apps/bridge/AGENTS.md](../apps/bridge/AGENTS.md)
