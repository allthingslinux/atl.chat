# Production Deployment Guide

Deploy the atl.chat stack on a server behind an Nginx Proxy Manager (NPM) reverse proxy.

## Architecture

```
Internet                          Tailscale Mesh
   │                         ┌──────────────────────┐
   │  DNS:                   │                      │
   │  *.atl.chat → NPM IP   │  Server A (NPM)      │  Server B (atl.chat)
   │                         │  100.64.1.0           │  100.64.7.0
   ▼                         │                      │
┌──────┐                     │  Nginx Proxy Manager  │  UnrealIRCd (:6697,:8000,:8600)
│Client├────:443/:6697──────►│  :80 → HTTPS redirect │  Atheme (shares irc network)
│      │                     │  :443 → reverse proxy │  Prosody (:5222-5281)
└──────┘                     │  :6697 → TCP stream   │  XMPP Nginx (:5281) [optional]
                             │  :5222 → TCP stream   │  Bridge
                             │                      │  The Lounge (:9000)
                             └──────────────────────┘  WebPanel (:8080)
```

Both servers connected via Tailscale (or WireGuard/VPN). Public DNS points to Server A.
NPM on Server A reverse-proxies to Server B's private Tailscale IP.

---

## Prerequisites

- **Server A:** Nginx Proxy Manager installed, public IP, Tailscale joined
- **Server B:** Docker + Docker Compose, `just`, `git`, Tailscale joined
- **DNS:** Domain with Cloudflare DNS (for cert-manager DNS-01 challenge)
- **Tailscale:** Both servers on the same tailnet

---

## Step 1: Server B — Clone and Configure

```bash
git clone https://github.com/allthingslinux/atl.chat.git
cd atl.chat
cp .env.example .env
```

Edit `.env` — change these from defaults:

```bash
# ── Core ──
ATL_ENVIRONMENT=prod
ATL_GATEWAY_IP=100.64.1.0          # Server A's Tailscale IP
ATL_CHAT_IP=100.64.7.0             # Server B's Tailscale IP

# ── Certs (Cloudflare DNS challenge) ──
CLOUDFLARE_DNS_API_TOKEN=<your-cloudflare-api-token>
LETSENCRYPT_EMAIL=admin@allthingslinux.org

# ── IRC ──
IRC_DOMAIN=irc.atl.chat
IRC_ROOT_DOMAIN=atl.chat
IRC_SSL_CERT_PATH=/home/unrealircd/unrealircd/certs/live/irc.atl.chat/fullchain.pem
IRC_SSL_KEY_PATH=/home/unrealircd/unrealircd/certs/live/irc.atl.chat/privkey.pem

# CHANGE ALL THESE from defaults:
IRC_OPER_PASSWORD=<argon2id-hash>   # Generate: just irc mkpasswd
IRC_DRPASS=<argon2id-hash>
IRC_SERVICES_PASSWORD=<strong-random>
ATL_WEBIRC_PASSWORD=<strong-random>
WEBPANEL_RPC_USER=<username>
WEBPANEL_RPC_PASSWORD=<strong-random>
THELOUNGE_WEBIRC_PASSWORD=<strong-random>

# Regenerate cloak keys:
# just irc gencloak

# ── XMPP ──
XMPP_DOMAIN=atl.chat
PROSODY_SSL_KEY=certs/live/atl.chat/privkey.pem
PROSODY_SSL_CERT=certs/live/atl.chat/fullchain.pem
PROSODY_UPLOAD_EXTERNAL_URL=https://xmpp.atl.chat/upload/
PROSODY_PROXY_ADDRESS=atl.chat
PROSODY_SERVER_NAME=atl.chat
PROSODY_SERVER_WEBSITE=https://atl.chat
PROSODY_SERVER_DESCRIPTION="All Things Linux XMPP"

# If NPM handles HTTPS for XMPP (recommended):
# PROSODY_HTTPS_VIA_PROXY=true

# ── TURN ──
TURN_SECRET=<strong-random-shared-with-coturn>
TURN_EXTERNAL_HOST=turn.atl.network

# ── Bridge ──
BRIDGE_DISCORD_TOKEN=<your-discord-bot-token>
BRIDGE_DISCORD_CHANNEL_ID=<your-discord-channel-id>
BRIDGE_XMPP_COMPONENT_JID=bridge.atl.chat
BRIDGE_XMPP_COMPONENT_SECRET=<strong-random>

# STS (start conservative, increase after testing):
IRC_STS_DURATION=1d
IRC_STS_PRELOAD=no

# Portal (if using):
# BRIDGE_PORTAL_BASE_URL=https://portal.atl.tools
# BRIDGE_PORTAL_TOKEN=<token>
```

**Do NOT create `.env.dev`** — the prod flow should not load dev overrides.

---

## Step 2: Server B — Initialize and Start

```bash
# Install just if not present
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin

# Initialize (creates data dirs, generates configs, obtains certs)
just prod

# Check all services are healthy
just status

# Follow logs for issues
just logs
```

The `just prod` command:

1. Runs `scripts/init.sh` which creates `data/` directories, generates configs from
   templates, and generates self-signed certs as fallback
2. Starts `docker compose --env-file .env up -d`

The cert-manager container will attempt to obtain Let's Encrypt certs via Cloudflare
DNS-01 challenge. Check its logs:

```bash
docker compose logs cert-manager
```

---

## Step 3: DNS Records

Point these at **Server A** (the NPM host's public IP):

| Record | Type | Value | Purpose |
|--------|------|-------|---------|
| `irc.atl.chat` | A | `<Server A public IP>` | IRC server |
| `atl.chat` | A | `<Server A public IP>` | XMPP (VirtualHost domain) |
| `xmpp.atl.chat` | CNAME | `atl.chat` | XMPP HTTP services (BOSH, WebSocket, upload) |
| `webirc.atl.chat` | CNAME | `atl.chat` | The Lounge web IRC client |
| `panel.atl.chat` | CNAME | `atl.chat` | UnrealIRCd WebPanel |

### XMPP SRV Records

These tell XMPP clients and servers where to connect. Point at `xmpp.atl.chat`
(which resolves to Server A / NPM):

| Record | Type | Priority | Weight | Port | Target |
|--------|------|----------|--------|------|--------|
| `_xmpp-client._tcp.atl.chat` | SRV | 0 | 5 | 5222 | `xmpp.atl.chat` |
| `_xmpps-client._tcp.atl.chat` | SRV | 0 | 5 | 5223 | `xmpp.atl.chat` |
| `_xmpp-server._tcp.atl.chat` | SRV | 0 | 5 | 5269 | `xmpp.atl.chat` |
| `_xmpps-server._tcp.atl.chat` | SRV | 0 | 5 | 5270 | `xmpp.atl.chat` |

### XMPP Component Records (optional, for federation)

| Record | Type | Value |
|--------|------|-------|
| `muc.atl.chat` | CNAME | `atl.chat` |
| `upload.atl.chat` | CNAME | `atl.chat` |
| `proxy.atl.chat` | CNAME | `atl.chat` |
| `pubsub.atl.chat` | CNAME | `atl.chat` |

---

## Step 4: NPM Configuration — Server A

### HTTP Proxy Hosts (HTTPS termination at NPM)

For these services, NPM terminates TLS and proxies to Server B over the Tailscale mesh.

| Domain | Scheme | Forward Host | Forward Port | Websocket | SSL |
|--------|--------|-------------|--------------|-----------|-----|
| `xmpp.atl.chat` | http | `100.64.7.0` | `5280` | ✅ | Let's Encrypt |
| `webirc.atl.chat` | http | `100.64.7.0` | `9000` | ✅ | Let's Encrypt |
| `panel.atl.chat` | http | `100.64.7.0` | `8080` | ❌ | Let's Encrypt |

For each:

1. NPM → Proxy Hosts → Add Proxy Host
2. Domain: `xmpp.atl.chat`
3. Scheme: `http`, Forward Hostname: `100.64.7.0`, Port: `5280`
4. Enable "Websockets Support" (required for BOSH and WebSocket)
5. SSL tab → Request new Let's Encrypt certificate, enable "Force SSL"
6. Custom Nginx Config (Advanced tab) for XMPP:

```nginx
# Increase timeouts for long-lived BOSH/WebSocket connections
proxy_read_timeout 900s;
proxy_send_timeout 900s;

# WebSocket upgrade headers (NPM adds these when Websocket is checked,
# but explicit config ensures correct behavior)
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

### IRC WebSocket (via HTTP proxy)

The IRC WebSocket on port 8000 can also go through an HTTP proxy host:

| Domain | Scheme | Forward Host | Forward Port | Websocket | SSL |
|--------|--------|-------------|--------------|-----------|-----|
| `irc.atl.chat` | http | `100.64.7.0` | `8000` | ✅ | Let's Encrypt |

This handles `wss://irc.atl.chat/ws` connections from web clients.

### TCP Stream Proxies (TLS passthrough)

For non-HTTP protocols, NPM forwards raw TCP. Server B handles TLS.

In NPM → Streams → Add Stream:

| Incoming Port | Forward Host | Forward Port | PROXY Protocol |
|---------------|-------------|--------------|----------------|
| `6697` | `100.64.7.0` | `6697` | ❌ |
| `5222` | `100.64.7.0` | `5222` | ❌ |
| `5223` | `100.64.7.0` | `5223` | ❌ |
| `5269` | `100.64.7.0` | `5269` | ❌ |
| `5270` | `100.64.7.0` | `5270` | ❌ |

**Note on real client IPs:** Two mechanisms handle real-IP forwarding:

- **WebSocket (port 8000):** NPM sends `X-Forwarded-For` headers. The `proxy npm-x-forwarded`
  block in UnrealIRCd trusts these from the gateway IP and Tailscale range. Hosts matching
  this are auto-exempted from connect floods and blacklist checks (UnrealIRCd 6.1.8+).
- **WEBIRC (The Lounge, KiwiIRC):** Web gateways send the real client IP via the WEBIRC
  protocol. The `proxy npm-webirc` block trusts the gateway for this.
- **Raw TCP streams (port 6697):** UnrealIRCd does not support HAProxy PROXY Protocol.
  Direct IRC clients through NPM TCP streams will appear as the proxy IP. This is an
  upstream limitation — see the [Proxy block docs](https://www.unrealircd.org/docs/Proxy_block).

**XMPP ports:** Prosody doesn't support PROXY Protocol on C2S/S2S either. The
`trusted_proxies` config handles X-Forwarded-For for HTTP endpoints, and S2S
authenticates by domain (not IP) via XMPP dialback or certificates.

---

## Step 5: Verify

### IRC

```bash
# From your local machine — connect through NPM
openssl s_client -connect irc.atl.chat:6697

# Should see the UnrealIRCd TLS certificate and IRC welcome
```

### XMPP

```bash
# Test BOSH endpoint through NPM
curl -sf https://xmpp.atl.chat/http-bind

# Test with an XMPP client (Conversations, Gajim, etc.)
# Account: user@atl.chat, Server: atl.chat
```

### Web Clients

- The Lounge: `https://webirc.atl.chat`
- Converse.js: `https://xmpp.atl.chat/conversejs`
- WebPanel: `https://panel.atl.chat`

### Prosody Connectivity Check

```bash
docker exec atl-xmpp-server prosodyctl check connectivity
docker exec atl-xmpp-server prosodyctl check dns
docker exec atl-xmpp-server prosodyctl check certs
```

### IM Observatory

Test your XMPP server compliance at: <https://check.messaging.one/>

---

## Certificate Renewal

Certs are obtained by the cert-manager container (Lego + Cloudflare DNS-01).
They are stored in `data/certs/live/<domain>/`.

After renewal, services need to reload:

```bash
# Reload IRC (picks up new certs without restart)
docker exec atl-irc-server /home/unrealircd/unrealircd/bin/unrealircdctl rehash

# Reload Prosody
docker exec atl-xmpp-server prosodyctl reload

# The Lounge reads certs on connection — restart to pick up new certs
docker compose restart atl-thelounge
```

To automate, add a cron job on Server B:

```bash
# /etc/cron.weekly/atl-cert-reload
#!/bin/bash
cd /path/to/atl.chat
docker exec atl-irc-server /home/unrealircd/unrealircd/bin/unrealircdctl rehash
docker exec atl-xmpp-server prosodyctl reload
docker compose restart atl-thelounge
```

---

## Security Checklist

- [ ] All `change_me_*` passwords replaced with strong random values
- [ ] Cloak keys regenerated (`just irc gencloak`)
- [ ] Oper password is argon2id hash (not plaintext)
- [ ] `CLOUDFLARE_DNS_API_TOKEN` set (scoped to DNS edit only)
- [ ] `.env` file permissions: `chmod 600 .env`
- [ ] `data/` directory permissions: `chmod 700 data/`
- [ ] No `.env.dev` file exists on prod server
- [ ] `ATL_ENVIRONMENT=prod` (not `dev`)
- [ ] IRC STS duration increased after testing (1d → 30d → 180d)
- [ ] Prosody `s2s_secure_auth=true` (default in `.env.example`)
- [ ] NPM SSL certificates obtained and forced
- [ ] Firewall: only 80, 443, 6697, 5222, 5223, 5269, 5270 open to public

---

## Backup Strategy

```bash
# Backup all persistent data
tar czf atl-chat-backup-$(date +%Y%m%d).tar.gz \
  data/ \
  .env \
  apps/unrealircd/config/unrealircd.conf \
  apps/atheme/config/atheme.conf \
  apps/bridge/config.yaml

# Critical data:
# data/irc/data/         — UnrealIRCd runtime (tkl.db, reputation.db)
# data/atheme/data/      — Atheme services DB (nickserv, chanserv registrations)
# data/xmpp/data/        — Prosody SQLite (accounts, MAM archives)
# data/certs/            — TLS certificates
# data/thelounge/        — The Lounge user data
```

Schedule daily backups to off-site storage.

---

## Troubleshooting

### Bridge can't connect to IRC

Check `docker compose logs atl-bridge`. Common causes:

- G-Line from DNSBL: The `except ban` block covers Docker IPs (`172.16.0.0/12`).
  If the bridge connects from Tailscale, add `100.64.0.0/10` to the except block.
- TLS verification: Set `BRIDGE_IRC_TLS_VERIFY=false` if using self-signed certs.
  For prod with real certs, leave `true` (default).

### XMPP federation not working

```bash
docker exec atl-xmpp-server prosodyctl check dns
docker exec atl-xmpp-server prosodyctl check connectivity
```

Common causes:

- Missing SRV records (see DNS section above)
- Port 5269 not forwarded through NPM streams
- `s2s_secure_auth=true` but cert doesn't cover the domain (check with `prosodyctl check certs`)

### Certs not renewing

```bash
docker compose logs cert-manager
```

Common causes:

- `CLOUDFLARE_DNS_API_TOKEN` not set or expired
- Cloudflare API token doesn't have DNS edit permissions for the zone
- Rate limited by Let's Encrypt (check https://letsencrypt.org/docs/rate-limits/)

### WebSocket connections failing

Ensure NPM proxy hosts have "Websockets Support" enabled. For XMPP BOSH/WebSocket,
the proxy timeout must be long enough (default 60s is too short):

```nginx
proxy_read_timeout 900s;
```
