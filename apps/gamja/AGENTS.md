# Gamja (IRC Web Client)

> Scope: IRC web client app (planned). Inherits monorepo [AGENTS.md](../../AGENTS.md).

Gamja — lightweight IRC web client. Currently planned; Containerfile and config scaffolding in place.

## Tech Stack

Gamja · Node.js · Docker

## Repository Structure

```
config/
└── config.json        # Server/OAuth2 config (example values)

default/
└── config.json        # Default config template

Containerfile          # Multi-stage: node-alpine, npm install
```

## Related

- [Monorepo AGENTS.md](../../AGENTS.md)
- [apps/thelounge/AGENTS.md](../thelounge/AGENTS.md)
