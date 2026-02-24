# Global Infrastructure & Networking

This document outlines the standard networking topology, port allocations, and SSL/DNS patterns for the `atl.chat` ecosystem within the broader All Things Linux Tailnet.

## Network Topology

We operate on a distributed "VPC" using Tailscale's CGNAT subnet: `100.64.0.0/10`.

- **Internal Gateway**: `atl.network` (Tailnet IP: `100.64.1.0`)
- **Chat Services**: `atl.chat` (Tailnet IP: `100.64.7.0`)

### Traffic Flow

1. **HTTP/S Traffic**:
   `Internet` -> `Cloudflare` -> `atl.network` (Nginx Proxy Manager) -> `Tailnet` -> `atl.chat` (Containers)

2. **TCP/UDP (IRC/XMPP) Traffic**:
   `Internet` -> `atl.network` (NPM Stream Pass-through) -> `Tailnet` -> `atl.chat` (TCP Ports)

---

## Global Port Registry

To avoid collisions and simplify proxy configuration, we use standardized port allocations.

| Service | Port | Protocol | Description |
| :--- | :--- | :--- | :--- |
| **IRC** | 6667 | TCP | Plaintext Client Connection |
| **IRC** | 6697 | TCP | SSL/TLS Client Connection |
| **IRC** | 7000 | TCP | WebIRC / WebSocket |
| **XMPP** | 5222 | TCP | Client-to-Server (C2S) |
| **XMPP** | 5269 | TCP | Server-to-Server (S2S) |
| **XMPP** | 5280 | TCP | HTTP (BOSH/Websockets) |
| **XMPP** | 5281 | TCP | HTTPS (BOSH/Websockets) |
| **Web** | 80/443 | TCP | Standard HTTP/S |

---

## SSL & DNS Strategy

### Hostnames

Standardize on Tailnet DNS for internal service discovery (e.g., `irc.atl.chat.tailnet-name.ts.net`).

### Certificates

- **Termination**: Handled at `atl.network` (Nginx Proxy Manager).
- **Renewal**: Automatic via Cloudflare DNS-01 challenges.
- **Internal Transport**: Tailscale provides wireguard-level encryption between all nodes in the mesh.
