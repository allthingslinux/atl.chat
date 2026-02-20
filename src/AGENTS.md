# src/

> Scope: `src/` — inherits root [AGENTS.md](../AGENTS.md).

Contains the single installable package: `bridge`.

## Structure

```
src/bridge/          # The bridge package (entry point: __main__.py)
├── __main__.py      # Entry point + signal handling
├── config.py        # YAML config + env overlay
├── events.py        # Event dataclasses + factory functions
├── identity.py      # Portal API client + TTL cache
├── gateway/         # Bus, Relay, Router
├── formatting/      # Discord↔IRC format converters
└── adapters/        # Discord, IRC, XMPP protocol adapters
```

## Related

- [bridge/gateway/AGENTS.md](bridge/gateway/AGENTS.md)
- [bridge/adapters/AGENTS.md](bridge/adapters/AGENTS.md)
- [bridge/formatting/AGENTS.md](bridge/formatting/AGENTS.md)
- [Root AGENTS.md](../AGENTS.md)
