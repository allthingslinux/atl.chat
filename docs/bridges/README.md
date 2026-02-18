# Bridge Infrastructure

Overview of protocol bridging in atl.chat.

## Bridges

- **[Biboumi](../../apps/bridge/biboumi/)** – XMPP-to-IRC gateway
- **[Matterbridge](../../apps/bridge/matterbridge/)** – Multi-protocol relay

## Compose

Bridge services are defined in `infra/compose/bridge.yaml`. They use the shared `atl-chat` network to connect to IRC and XMPP.

## See Also

- [apps/bridge/README.md](../../apps/bridge/README.md) – Bridge design and setup
- [Networking](../infra/networking.md) – Port allocations
