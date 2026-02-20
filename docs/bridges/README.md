# Bridge Infrastructure

Overview of protocol bridging in atl.chat.

## Bridge

- **[ATL Bridge](../../apps/bridge/)** – Custom Discord–IRC–XMPP multi-presence bridge

## Compose

Bridge services are defined in `infra/compose/bridge.yaml`. The bridge attaches to the shared `atl-chat` network and connects to both IRC and XMPP internally.

## See Also

- [apps/bridge/README.md](../../apps/bridge/README.md) – Bridge setup and configuration
- [Networking](../infra/networking.md) – Port allocations
