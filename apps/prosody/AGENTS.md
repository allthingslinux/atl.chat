# Prosody (XMPP)

> Scope: XMPP server app. Inherits monorepo [AGENTS.md](../../AGENTS.md).

Prosody XMPP server with Lua config. Loaded via root: `just xmpp`.

## Tech Stack

Prosody · Lua config · Docker · PostgreSQL (optional, for storage)

## Repository Structure

```
config/
└── prosody.cfg.lua    # Main Prosody config

scripts/               # Container scripts
www/                   # Static assets
Containerfile
docker-entrypoint.sh
justfile               # Loaded via: mod xmpp './apps/prosody'
modules.list
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `just xmpp shell` | Bash into Prosody container |
| `just xmpp reload` | Reload Prosody config |
| `just xmpp adduser [user]` | Add XMPP user |
| `just xmpp deluser [user]` | Delete XMPP user |
| `just xmpp db-backup` | Backup database |
| `just xmpp check-cert [domain]` | Check certificate |

## Related

- [Monorepo AGENTS.md](../../AGENTS.md)
- [docs/services/xmpp/](../../docs/services/xmpp/)
