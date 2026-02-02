# Documentation Hub: atl.chat Monorepo

Welcome to the centralized documentation hub for the `atl.chat` ecosystem. This monorepo manages multiple communication protocols (IRC, XMPP, Bridges) using a unified infrastructure.

## 🚀 Getting Started
- **[Onboarding Guide](./onboarding/README.md)** - Getting your local environment set up with `just` and `lefthook`.
- **[Architecture Overview](./architecture/README.md)** - How the different services interact.
- **[Networking & Port Registry](./infra/networking.md)** - Tailscale VPC topology and port allocations.

## 🏗️ Infrastructure Standards
- **[Containerization](./infra/containerization.md)** - Standardized Docker patterns and orchestration.
- **[SSL/TLS Termination](./infra/ssl.md)** - Centralized security via the `atl.network` gateway.
- **[CI/CD Pipeline](./architecture/ci-cd.md)** - Automated testing and deployment workflows.

## 🔌 Services & Protocols
Learn more about the specific applications in this monorepo:

### Core Services
- **[IRC (UnrealIRCd)](./services/irc/README.md)** - high-performance, secure IRC server.
- **[XMPP (Prosody)](./services/xmpp/README.md)** - Modern, extensible XMPP server.
- **[Web Client](./services/web/README.md)** - Next.js frontend for the chat ecosystem.

### Bridging & Interoperability
- **[Bridge Infrastructure](./bridges/README.md)** - Overview of protocol bridging logic.
- **[Biboumi](../apps/bridge/biboumi/README.md)** - XMPP-to-IRC gateway.
- **[Matterbridge](../apps/bridge/matterbridge/README.md)** - Multi-protocol message relay.

---
> [!NOTE]
> If you are adding a new service, please follow our [Service Integration Guide](./architecture/new-service.md).
