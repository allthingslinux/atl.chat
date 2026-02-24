# XMPP DNS Configuration

XMPP relies on DNS for client discovery and server-to-server federation. This document describes the DNS records required for atl.chat's Prosody deployment.

## Domain Layout

| Role | Domain | Purpose |
|------|--------|---------|
| VirtualHost (user JIDs) | `atl.chat` | `user@atl.chat` |
| HTTP/BOSH host | `xmpp.atl.chat` | Web clients, BOSH, WebSocket |
| MUC | `muc.atl.chat` | Chat rooms |
| Upload | `upload.atl.chat` | File sharing (XEP-0363) |
| Proxy | `proxy.atl.chat` | SOCKS5 proxy (XEP-0065) |
| PubSub | `pubsub.atl.chat` | Publish-Subscribe, feeds (XEP-0060) |
| Bridge | `bridge.atl.chat` | XMPP component |

## A Records

A records are the minimum. If the XMPP server runs on the same host as the domain, add:

- `atl.chat` → server IP
- `xmpp.atl.chat` → server IP
- `muc.atl.chat` → server IP
- `upload.atl.chat` → server IP
- `proxy.atl.chat` → server IP
- `pubsub.atl.chat` → server IP
- `bridge.atl.chat` → server IP

Or use a wildcard: `*.atl.chat` → server IP.

## SRV Records (Recommended)

If the XMPP service runs on a different host (e.g. `xmpp.atl.chat`) than the user domain (`atl.chat`), use SRV records:

| Record | TTL | Type | Priority | Weight | Port | Target |
|--------|-----|------|----------|--------|------|--------|
| `_xmpp-client._tcp.atl.chat` | 3600 | SRV | 0 | 5 | 5222 | `xmpp.atl.chat` |
| `_xmpp-server._tcp.atl.chat` | 3600 | SRV | 0 | 5 | 5269 | `xmpp.atl.chat` |
| `_xmpps-client._tcp.atl.chat` | 3600 | SRV | 0 | 5 | 5223 | `xmpp.atl.chat` |
| `_xmpps-server._tcp.atl.chat` | 3600 | SRV | 0 | 5 | 5270 | `xmpp.atl.chat` |

For Direct TLS (XEP-0368), the `_xmpps` records use ports 5223 and 5270.

### Subdomain SRV (S2S Federation)

If MUC/upload/proxy run on subdomains and need federation access:

| Record | TTL | Type | Priority | Weight | Port | Target |
|--------|-----|------|----------|--------|------|--------|
| `_xmpp-server._tcp.muc.atl.chat` | 3600 | SRV | 0 | 5 | 5269 | `xmpp.atl.chat` |
| `_xmpp-server._tcp.upload.atl.chat` | 3600 | SRV | 0 | 5 | 5269 | `xmpp.atl.chat` |
| `_xmpp-server._tcp.proxy.atl.chat` | 3600 | SRV | 0 | 5 | 5269 | `xmpp.atl.chat` |
| `_xmpp-server._tcp.pubsub.atl.chat` | 3600 | SRV | 0 | 5 | 5269 | `xmpp.atl.chat` |

## Verification

### Certificate configuration

```bash
just xmpp check-certs
```

### DNS records

Run Prosody's DNS check:

```bash
just xmpp check-dns
```

Or directly:

```bash
docker compose exec atl-xmpp-server prosodyctl check dns
```

## XEP-0156 discovery

Clients use HTTPS lookup (XEP-0156) for BOSH/WebSocket discovery. `/.well-known/host-meta` is served by Prosody and proxied by nginx. Do **not** use `_xmppconnect` TXT records; they are insecure.

## Certificates

Certificates must cover the VirtualHost domain and any component subdomains. See [SSL Strategy](../../infra/ssl.md) and certificate SANs in `scripts/init.sh` / `apps/prosody/docker-entrypoint.sh`.

## References

- [Prosody DNS documentation](https://prosody.im/doc/dns)
- [XEP-0156: Discovering Alternative XMPP Connection Methods](https://xmpp.org/extensions/xep-0156.html)
- [XEP-0368: SRV records for XMPP over TLS](https://xmpp.org/extensions/xep-0368.html)
