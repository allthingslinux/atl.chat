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
| `turn-standalone/` | Standalone TURN/STUN for edge deployment |

## Usage

- Main stack: `docker compose up -d` (from repo root)
- TURN standalone: `docker compose -f infra/turn-standalone/compose.yaml up -d`

## Related

- [Monorepo AGENTS.md](../AGENTS.md)
- [docs/infra/](../docs/infra/) — Containerization, networking, SSL docs
