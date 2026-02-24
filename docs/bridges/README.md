# Bridge Infrastructure

Overview of protocol bridging in atl.chat.

## Bridge

The [apps/bridge/](../../apps/bridge/) in-repo package provides Discord↔IRC↔XMPP bridging. It connects to UnrealIRCd, Prosody, and Discord to relay messages across protocols.

## Compose

Bridge services are defined in `infra/compose/bridge.yaml`. They use the shared `atl-chat` network to connect to IRC and XMPP.

## See Also

- [apps/bridge/README.md](../../apps/bridge/README.md) – Bridge design and setup
- [Networking](../infra/networking.md) – Port allocations
