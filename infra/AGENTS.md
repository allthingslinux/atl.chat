# Infrastructure

> Scope: `infra/` — inherits [AGENTS.md](../AGENTS.md).

Docker Compose fragments and TURN server. Root `compose.yaml` includes `infra/compose/*.yaml`.

## Structure

| Dir / File | Purpose |
|------------|---------|
| `compose/irc.yaml` | UnrealIRCd, Atheme, WebPanel |
| `compose/xmpp.yaml` | Prosody |
| `compose/bridge.yaml` | Discord↔IRC↔XMPP bridge |
| `compose/thelounge.yaml` | The Lounge web IRC client |
| `compose/cert-manager.yaml` | Lego (Let's Encrypt) |
| `compose/networks.yaml` | Shared `atl-chat` network |
| `nginx/` | Nginx config for Prosody HTTPS (docker-entrypoint, Dockerfile, prosody-https.conf.template) |
| `turn-standalone/` | Standalone TURN/STUN for edge deployment |

## Security

All services use `cap_drop: ALL` + `security_opt: no-new-privileges:true`. Services that need privilege-drop (prosody, nginx, webpanel) additionally have `cap_add: [SETUID, SETGID]`.

## Usage

- Main stack: `docker compose up -d` (from repo root)
- TURN standalone: `docker compose -f infra/turn-standalone/compose.yaml up -d`

## Related

- [Monorepo AGENTS.md](../AGENTS.md)
- [docs-old/infra/](../docs-old/infra/) — Containerization, networking, SSL docs
