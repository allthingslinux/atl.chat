# Infrastructure

Infrastructure as code for ATL chat services.

## Structure

- `compose/` - Compose fragments included by root `compose.yaml` (irc, xmpp, bridge, cert-manager, networks)
- `turn-standalone/` - Standalone TURN/STUN server for edge deployment (atl.network)

## Usage

- Main stack: `docker compose up -d` (from repo root)
- Cert-manager: Part of main stack; scripts in `scripts/cert-manager/`; runs Lego for Let's Encrypt via Cloudflare DNS-01
- TURN standalone: `docker compose -f infra/turn-standalone/compose.yaml up -d` (for edge server)
