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

- **Upstream:** [unrealircd/unrealircd-webpanel](https://github.com/unrealircd/unrealircd-webpanel)
- **Access:** <http://localhost:8080> (dev)
- **RPC:** UnrealIRCd JSON-RPC on port 8600
- **Data:** `data/irc/webpanel-data` → `/var/www/html/unrealircd-webpanel/data`

## Related

- [Monorepo AGENTS.md](../../AGENTS.md)
- [apps/unrealircd/AGENTS.md](../unrealircd/AGENTS.md)
- [docs/services/irc/WEBPANEL.md](../../docs/services/irc/WEBPANEL.md)
