# WebPanel (UnrealIRCd Web Admin)

> Scope: UnrealIRCd web admin app. Inherits monorepo [AGENTS.md](../../AGENTS.md).

UnrealIRCd WebPanel — web-based administration for IRC network. No justfile mod; runs as Docker service via `infra/compose/irc.yaml`.

## Tech Stack

UnrealIRCd WebPanel · PHP 8.4 · Nginx · Docker (multi-stage: composer + trafex/php-nginx)

## Repository Structure

```
Containerfile     # Multi-stage: clone upstream, composer install, php-nginx
nginx.conf       # Nginx proxy config (root, logs)
README.md        # User docs, access, troubleshooting
```

## Key Facts

- **Upstream:** [unrealircd/unrealircd-webpanel](https://github.com/unrealircd/unrealircd-webpanel) — pinned to branch `0.9.1`
- **Access:** <http://localhost:8080> (dev)
- **RPC:** UnrealIRCd JSON-RPC on port 8600
- **Data:** `data/irc/webpanel-data` → `/var/www/html/data`
- **Security:** `cap_drop: ALL` + `cap_add: SETUID, SETGID` in compose

## Related

- [Monorepo AGENTS.md](../../AGENTS.md)
- [apps/unrealircd/AGENTS.md](../unrealircd/AGENTS.md)
- [docs-old/services/irc/WEBPANEL.md](../../docs-old/services/irc/WEBPANEL.md)
