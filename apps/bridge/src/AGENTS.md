# src/

> Scope: `src/` — inherits root [AGENTS.md](../AGENTS.md).

Contains the single installable package: `bridge`.

## Structure

```
src/bridge/          # The bridge package (entry point: __main__.py)
├── __main__.py      # Entry point + signal handling
├── events.py        # Re-export from core.events
├── errors.py        # Re-export from core.errors
├── config/          # YAML config + env overlay (loader, schema)
├── core/            # Constants, events, errors
├── identity/        # Portal API + dev resolver
├── gateway/         # Bus, Relay, Router, MessageIDResolver
├── formatting/      # Discord↔IRC format converters
└── adapters/        # discord/, irc/, xmpp/ protocol packages
```

## Related

- [Bridge AGENTS.md](../AGENTS.md)
- [bridge/gateway/AGENTS.md](bridge/gateway/AGENTS.md)
- [bridge/adapters/AGENTS.md](bridge/adapters/AGENTS.md)
- [bridge/formatting/AGENTS.md](bridge/formatting/AGENTS.md)
