# Dev vs Prod Lifecycle Audit

**Date:** 2026-02-26
**Scope:** Full trace of dev and prod setup flows — env, scripts, Docker, TLS, DNS, config templates

---

## Executive Summary

The dev story is **solid and works well**. The prod story has **real gaps** that would block a production deployment. The main issues are: `just prod` doesn't run `init.sh` or load env files; the cert-manager is a placeholder that doesn't actually issue certs; the prod profiles don't actually differentiate services; and there's no documentation for the prod deployment path.

**Verdict:** Dev is ~90% clean. Prod is ~40% ready.

---

## Dev Flow Trace (`just dev`)

### What happens

```
just dev
  → sources .env.dev (sets ATL_ENVIRONMENT=dev, IRC_DOMAIN=irc.localhost, etc.)
  → runs scripts/init.sh:
      1. Creates data/ directories (irc, atheme, xmpp, thelounge, certs)
      2. Sets permissions (chown/chmod)
      3. Copies system CA bundle to apps/unrealircd/config/tls/
      4. Generates self-signed certs for irc.localhost and xmpp.localhost
      5. Copies .env.example → .env (if .env missing)
      6. Runs prepare-config.sh:
          - Sources .env then .env.dev
          - envsubst on unrealircd.conf.template → unrealircd.conf
          - envsubst on atheme.conf.template → atheme.conf
          - envsubst on bridge config.template.yaml → config.yaml
          - envsubst on thelounge config.js.template → config.js
  → docker compose --env-file .env --env-file .env.dev --profile dev up -d
```

### Dev Flow Verdict: 🟢 Works well

| Aspect | Status | Notes |
|--------|--------|-------|
| Env loading | 🟢 | `.env` base + `.env.dev` overlay, compose loads both via `--env-file` |
| Init script | 🟢 | Creates dirs, generates self-signed certs, generates configs |
| Config generation | 🟢 | `prepare-config.sh` sources both env files, envsubst works correctly |
| TLS (dev) | 🟢 | Self-signed certs auto-generated for `irc.localhost` and `xmpp.localhost` |
| Docker profile | 🟢 | `--profile dev` starts Dozzle log viewer |
| Port binding | 🟢 | `ATL_CHAT_IP=127.0.0.1` binds IRC ports to localhost only |
| Bridge TLS verify | 🟢 | `BRIDGE_IRC_TLS_VERIFY=false` skips cert verification for self-signed |
| Prosody TLS | 🟢 | `.env.dev` relaxes c2s/s2s encryption requirements |
| Storage | 🟢 | `PROSODY_STORAGE=sqlite` — no external DB needed |

---

## Prod Flow Trace (`just prod`)

### What happens

```
just prod
  → export ATL_ENVIRONMENT=prod (explicitly in justfile)
  → docker compose --profile prod up -d
```

That's it. **No init.sh. No env file loading. No config generation.**

### Prod Flow Verdict: 🔴 Broken

| Issue | Severity | Details |
|-------|----------|---------|
| **No init.sh** | 🔴 | `just prod` doesn't run `init.sh`. No `data/` dirs created, no configs generated from templates. If deploying to a fresh server, nothing works. |
| **No `--env-file`** | 🔴 | Unlike `just dev` which passes `--env-file .env --env-file .env.dev`, `just prod` passes nothing. Docker Compose will auto-load `.env` but there's no explicit prod overlay. All prod-specific overrides must be in `.env` itself. |
| **No prod profile differentiation** | 🟡 | The `profiles: ["dev"]` on Dozzle means it only starts with `--profile dev`. But no services have `profiles: ["prod"]`. So `just prod` starts the exact same services as `docker compose up -d` (everything except Dozzle). The profiles are meaningless for prod. |
| **Cert-manager is a placeholder** | 🔴 | The cert-manager service uses `goacme/lego:latest` with a custom `run.sh`, but it runs on every `docker compose up` — including dev where it's not needed. There's no `CLOUDFLARE_DNS_API_TOKEN` set in dev, so it likely errors silently. In prod, someone would need to set this token, but there's no documentation for the cert issuance flow. |
| **No prod documentation** | 🟡 | README says `just prod` starts production stack, but there's no guide for: initial prod setup, cert issuance, DNS records needed, secrets management, backup strategy. |

---

## TLS/Certificate Audit

### Dev TLS

```
init.sh → generate_dev_certs()
  → openssl req -x509 -nodes -days 365 -newkey rsa:2048
  → SANs: domain, *.domain, muc/upload/proxy/pubsub/bridge subdomains, localhost, 127.0.0.1
  → Stored in: data/certs/live/{irc.localhost,xmpp.localhost}/
```

| Aspect | Status | Notes |
|--------|--------|-------|
| Self-signed generation | 🟢 | Good SANs, RSA 2048, 365 days |
| IRC reads from | 🟢 | `data/certs` mounted as `/home/unrealircd/unrealircd/certs` |
| Prosody reads from | 🟢 | `data/certs` mounted as `/etc/prosody/certs` |
| Prosody entrypoint | 🟢 | Creates `https` symlinks for automatic HTTPS cert discovery |
| Bridge skips verify | 🟢 | `BRIDGE_IRC_TLS_VERIFY=false` in `.env.dev` |
| Prosody skips s2s auth | 🟢 | `PROSODY_S2S_SECURE_AUTH=false` in `.env.dev` |

### Prod TLS

| Aspect | Status | Notes |
|--------|--------|-------|
| Cert source | 🟡 | cert-manager (Lego/Cloudflare DNS) exists but is untested/undocumented |
| Cert path convention | 🟢 | Let's Encrypt layout: `data/certs/live/<domain>/fullchain.pem + privkey.pem` — matches both IRC and Prosody mount points |
| IRC cert paths | 🟢 | `IRC_SSL_CERT_PATH` in `.env.example` correctly points to `/home/unrealircd/unrealircd/certs/live/irc.atl.chat/fullchain.pem` |
| Prosody cert paths | 🟢 | `PROSODY_SSL_KEY/CERT` in `.env.example` are relative (`certs/live/localhost/...`) — **should be `certs/live/atl.chat/...` for prod** |
| XMPP nginx certs | 🟢 | `data/certs` mounted to nginx as `/etc/nginx/certs` |
| Cert renewal | 🔴 | No cron/timer for cert renewal. Lego container runs once and exits. No reload mechanism for IRC/Prosody after renewal. |
| Cert permissions | 🟢 | `init.sh` sets `chmod 644` on privkey.pem for container user access |

### TLS Config Issues

1. **Prosody `.env.example` cert paths say `localhost`:**

   ```
   PROSODY_SSL_KEY=certs/live/localhost/privkey.pem
   PROSODY_SSL_CERT=certs/live/localhost/fullchain.pem
   ```

   This is the **dev default baked into the "production" example file**. Should be the prod domain. The `.env.dev` override correctly switches to `xmpp.localhost`. But if someone copies `.env.example` for prod and forgets to change these, Prosody won't find its certs.

2. **No cert rotation/reload:**
   When certs renew (every 60-90 days with Let's Encrypt), the running daemons need to be told:
   - UnrealIRCd: `unrealircdctl rehash` or `kill -HUP`
   - Prosody: `prosodyctl reload`
   - The Lounge: restart container

   There's no hook for this.

---

## DNS Audit

### Dev DNS

Dev uses `.localhost` TLD — `irc.localhost`, `xmpp.localhost`. These resolve to `127.0.0.1` on most systems (RFC 6761). No DNS setup needed.

**However:** Inside Docker containers, `irc.localhost` does NOT resolve to the host — containers use Docker's internal DNS which only resolves container/service names. This is why the bridge uses Docker hostnames (`atl-irc-server`, `atl-xmpp-server`) instead of `irc.localhost`.

| Aspect | Status | Notes |
|--------|--------|-------|
| Host access | 🟢 | `irc.localhost:6697` works from host machine |
| Container-to-container | 🟢 | Uses Docker service names (`atl-irc-server`) |
| Browser access | 🟢 | `http://localhost:3000` (web), `http://localhost:9000` (Lounge) |
| XMPP client access | 🟡 | `xmpp.localhost` resolves on host but clients may not accept `.localhost` as a valid domain |

### Prod DNS

**No DNS setup documentation exists.** For production, operators would need:

| Record | Type | Target | Purpose |
|--------|------|--------|---------|
| `irc.atl.chat` | A/AAAA | server IP | IRC server |
| `xmpp.atl.chat` | A/AAAA | server IP | XMPP BOSH/WebSocket (via nginx) |
| `_xmpp-client._tcp.atl.chat` | SRV | `xmpp.atl.chat:5222` | XMPP C2S discovery |
| `_xmpps-client._tcp.atl.chat` | SRV | `xmpp.atl.chat:5223` | XMPP Direct TLS discovery |
| `_xmpp-server._tcp.atl.chat` | SRV | `xmpp.atl.chat:5269` | XMPP S2S federation |
| `_xmpps-server._tcp.atl.chat` | SRV | `xmpp.atl.chat:5270` | XMPP S2S Direct TLS |
| `muc.atl.chat` | CNAME | `xmpp.atl.chat` | MUC component |
| `upload.atl.chat` | CNAME | `xmpp.atl.chat` | HTTP file upload |
| `proxy.atl.chat` | CNAME | `xmpp.atl.chat` | SOCKS5 proxy |
| `pubsub.atl.chat` | CNAME | `xmpp.atl.chat` | PubSub |

---

## Docker Audit

### Profiles

| Profile | What it activates | Command |
|---------|-------------------|---------|
| `dev` | Dozzle only | `just dev` |
| `prod` | Nothing — no services use this profile | `just prod` |
| (none) | All services except Dozzle | `docker compose up -d` |

**Issue:** Prod profiles are empty. `just prod` is functionally identical to `docker compose up -d`. The profiles add no value.

### Image Strategy

| Service | Build | Image |
|---------|-------|-------|
| UnrealIRCd | `apps/unrealircd/Containerfile` | (local build) |
| Atheme | `apps/atheme/Containerfile` | (local build) |
| WebPanel | `apps/webpanel/Containerfile` | (local build) |
| Prosody | `apps/prosody/Containerfile` | `allthingslinux/prosody:latest` |
| XMPP Nginx | `infra/nginx/Dockerfile` | `allthingslinux/prosody-nginx:latest` |
| Bridge | `apps/bridge/Containerfile` | `ghcr.io/allthingslinux/bridge:latest` |
| The Lounge | (none) | `ghcr.io/thelounge/thelounge:latest` |
| Cert Manager | (none) | `goacme/lego:latest` |
| Dozzle | (none) | `amir20/dozzle:v8` |

**Issue:** Services with both `build:` and `image:` will use the pulled image if it exists, not the local build. This caused the bridge disconnect bug during dev setup. For dev, you want local builds. For prod, you want published images. Currently there's no way to switch — you'd need to `docker compose build` explicitly.

### Networking

All services are on a single `atl-chat` bridge network. Atheme uses `network_mode: service:atl-irc-server` (shares network namespace with UnrealIRCd). This is correct — Atheme connects to UnrealIRCd on `127.0.0.1:6901`.

### Port Binding

Dev: `ATL_CHAT_IP=127.0.0.1` binds IRC ports to localhost only.
Prod: `ATL_CHAT_IP=100.64.7.0` (Tailscale IP). XMPP, WebPanel, Lounge bind to `0.0.0.0` (all interfaces).

**Issue:** XMPP ports bind to `0.0.0.0` in both dev and prod (the xmpp.yaml doesn't use `ATL_CHAT_IP`). This means XMPP is publicly accessible even in dev. Not a security issue for localhost but inconsistent with IRC's approach.

---

## Script Audit

### `just dev` vs `just prod` asymmetry

```
just dev:
  1. Sources .env.dev  ← yes
  2. Runs init.sh      ← yes (creates dirs, generates certs, generates configs)
  3. Passes --env-file .env --env-file .env.dev  ← yes
  4. Uses --profile dev  ← yes

just prod:
  1. Sources nothing   ← no
  2. Runs nothing      ← no init.sh
  3. Passes nothing    ← no --env-file (relies on auto .env loading)
  4. Uses --profile prod  ← meaningless (no services use this profile)
```

This is the biggest structural problem. A first-time prod deployment would:

1. Clone repo
2. Create `.env` from `.env.example`
3. Run `just prod`
4. **Fail** because:
   - No `data/` directories exist
   - No configs generated from templates
   - No certs generated or obtained
   - Templates still have `${VAR}` placeholders

### `prepare-config.sh` always sources `.env.dev`

Line 57-63: The script unconditionally sources `.env.dev` if it exists. This means even if you're preparing prod configs, dev overrides would apply if `.env.dev` exists on the prod server. This is fine if `.env.dev` doesn't exist in prod, but it's a landmine.

---

## Findings Summary

### 🔴 CRITICAL

1. **`just prod` doesn't run `init.sh`** — no dirs, no certs, no config generation
2. **No cert renewal mechanism** — certs will expire with no reload
3. **Prosody `.env.example` cert paths default to `localhost`** — must be manually changed for prod

### 🟡 WARNING

1. **Prod profiles are empty** — `just prod` is identical to bare `docker compose up`
2. **No prod deployment documentation** — DNS records, cert issuance, secrets, backups
3. **`prepare-config.sh` always loads `.env.dev`** if present — prod configs could get dev overrides
4. **XMPP ports bind to 0.0.0.0** — inconsistent with IRC's `ATL_CHAT_IP` binding
5. **Docker images: local build vs pulled image ambiguity** — no clear strategy

### 🟢 OK

1. Dev flow works smoothly end-to-end
2. Env overlay pattern (.env + .env.dev) is clean
3. Self-signed cert generation covers all needed SANs
4. Config templates use envsubst consistently
5. Docker networking (shared namespace for Atheme, single bridge network) is correct
6. Data directory structure is well-organized

### 💡 SUGGESTIONS

1. **Create `just prod` parity with `just dev`**: Run `init.sh`, pass `--env-file`
2. **Add `.env.prod.example`** for production-specific overrides
3. **Add cert renewal cron** in cert-manager + post-renewal reload hooks
4. **Add `docs/deployment.md`** with prod setup guide
5. **Add XMPP SRV record documentation**
6. **Consider `docker compose build --no-cache` step for prod image freshness**

---

## Recommended Fix Priority

1. Fix `just prod` to run init and load env files
2. Fix Prosody `.env.example` cert paths to use `${XMPP_DOMAIN}` not `localhost`
3. Add prod deployment docs (DNS, certs, secrets)
4. Add cert renewal mechanism
5. Clean up meaningless profiles
