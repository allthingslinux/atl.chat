# The Lounge

> Scope: Web IRC client app. Inherits monorepo [AGENTS.md](../../AGENTS.md).

The Lounge web-based IRC client. Private mode (user accounts required). Defaults to ATL IRC server with WebIRC. Plugins: janitor (upload cleanup), giphy (`/giphy search|random`).

## Repository Structure

```
config.js.template   # Config template (env vars substituted at init)
justfile             # Loaded via: mod lounge './apps/thelounge'
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `just lounge add <name>` | Create user (prompts for password) |
| `just lounge list` | List users |
| `just lounge reset <name>` | Reset user password |

## Related

- [Monorepo AGENTS.md](../../AGENTS.md)
- [infra/AGENTS.md](../../infra/AGENTS.md)
