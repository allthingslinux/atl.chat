# Fluux Messenger (Docker image)

> Scope: `apps/fluux-messenger/` — inherits monorepo [AGENTS.md](../../AGENTS.md).

Build context for the **Fluux** XMPP web client (upstream [processone/fluux-messenger](https://github.com/processone/fluux-messenger)): multi-stage image clones a pinned tag, builds the Vite app, and serves static assets with **nginx**. Wired into the stack via [infra/compose/fluux-messenger.yaml](../../infra/compose/fluux-messenger.yaml) (`atl-fluux-messenger` service).

## Files

| File | Purpose |
|------|---------|
| `Containerfile` | Multi-stage build (clone, `pnpm build`, nginx runtime) |
| `docker-entrypoint.sh` | Substitute `FLUUX_DOMAIN` / cert paths into nginx config |
| `nginx-tls.conf.template` | HTTPS server block (shared cert mount) |
| `nginx-plain.conf.template` | HTTP-only variant |

## Environment (root `.env` / `.env.example`)

| Variable | Role |
|----------|------|
| `FLUUX_VERSION` | Git tag to build (build arg) |
| `FLUUX_DOMAIN` | Public hostname for the client |
| `FLUUX_CERT_DOMAIN` | Certificate / TLS identity helper for entrypoint |
| `FLUUX_MESSENGER_PORT` | Host → container `80` |
| `FLUUX_MESSENGER_HTTPS_PORT` | Host → container `443` |

## Related

- [infra/AGENTS.md](../../infra/AGENTS.md) — compose fragments
- [apps/docs/content/docs/reference/environment-variables.mdx](../docs/content/docs/reference/environment-variables.mdx) — full env reference (Fluux section)
