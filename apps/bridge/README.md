# Flexible Bridge Infrastructure

This directory contains configurations and orchestration for bridging services that connect different communication platforms (e.g., IRC, XMPP, Matrix, Discord).

## Design Philosophy

- **Service-Agnostic**: Each bridge is its own isolated component within a subdirectory.
- **Unified Orchestration**: Every bridge must include a `Containerfile` and be integrated into the root `compose.yaml` (using a specific profile).
- **Profile-Based**: Bridges should be assigned to the `bridge` Docker Compose profile to allow selective enablement.

## Supported Bridges

- **Matterbridge**: Versatile bridge supporting multiple protocols.
- **Biboumi**: Specialized XMPP gateway to IRC.
- **Others**: Ready to support new additions (Matrix-Appservice-IRC, etc.)

## Port Management

Refer to [Global Infrastructure & Networking](../../docs/infra/networking.md) for internal port allocations. Bridges should typically not expose ports publicly; they connect internally to the service containers.
