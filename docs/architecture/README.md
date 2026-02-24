# Architecture Overview

How the atl.chat services interact and communicate.

## Stack

- **IRC** (UnrealIRCd + Atheme) – Chat server and services
- **XMPP** (Prosody) – Modern messaging
- **Bridges** (apps/bridge) – Discord↔IRC↔XMPP protocol bridging
- **Web** (Next.js) – Landing and clients

## Compose Layout

All orchestration lives under `infra/compose/`. The root `compose.yaml` includes:

- `networks.yaml` – Shared `atl-chat` network
- `irc.yaml` – UnrealIRCd, Atheme, WebPanel
- `xmpp.yaml` – Prosody
- `cert-manager.yaml` – Let's Encrypt (Lego)
- `bridge.yaml` – Discord↔IRC↔XMPP bridge

## See Also

- [CI/CD Pipeline](./ci-cd.md)
- [New Service Guide](./new-service.md)
- [Networking](../../docs/infra/networking.md)
