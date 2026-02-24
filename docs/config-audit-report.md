# Config Audit Report — Sub-Apps Consistency Check

**Date:** 2025-02-23

## Summary

| Area | Status | Notes |
|------|--------|------|
| Root .env.example | ✅ | Single source of truth; comprehensive |
| init.sh env template path | ✅ | Fixed: uses `.env.example` |
| Bridge config | ⚠️ | config.example.yaml missing `irc_tls_verify` |
| Web .env.example | ✅ | Fixed: uses `NEXT_PUBLIC_IRC_WS_URL` |
| Docs (CONFIG.md, DEVELOPMENT.md) | ✅ | Fixed: reference `.env.example` |
| Compose env paths | ✅ | All use `path: ../../.env` correctly |
| XMPP/Prosody domain | ✅ | XMPP_DOMAIN → PROSODY_DOMAIN mapping correct |

---

## 1. init.sh — Wrong env template path ✅ FIXED

**File:** `scripts/init.sh` line 326

Changed `env.example` → `.env.example` so `create_env_template()` finds the template.

---

## 2. Bridge config.example.yaml — Missing irc_tls_verify ✅ FIXED

Added `irc_tls_verify: true` to `config.example.yaml` so users who copy the example get explicit TLS behavior.

---

## 3. Web .env.example — IRC websocket var name mismatch ✅ FIXED

Standardized on `NEXT_PUBLIC_IRC_WS_URL` in `apps/web/.env.example` to match root and justfile.

---

## 4. Docs — env.example vs .env.example ✅ FIXED

Updated CONFIG.md and DEVELOPMENT.md to reference `.env.example`.

---

## 5. Config flow verification

| Component | Config source | Status |
|-----------|---------------|-------|
| UnrealIRCd | `apps/unrealircd/config/unrealircd.conf` from template | ✅ |
| Atheme | `apps/atheme/config/atheme.conf` from template | ✅ |
| Prosody | `apps/prosody/config/prosody.cfg.lua` + env | ✅ |
| Bridge | `apps/bridge/config.yaml` from template or example | ✅ |
| Bridge compose | `../../apps/bridge/config.yaml` → `/app/config.yaml` | ✅ |

---

## 6. Env var coverage

**Bridge compose** (`infra/compose/bridge.yaml`): Passes `BRIDGE_DISCORD_TOKEN`, `BRIDGE_PORTAL_*`, `BRIDGE_XMPP_COMPONENT_*`, `BRIDGE_IRC_NICK`, `ATL_ENVIRONMENT`, `BRIDGE_IRC_TLS_VERIFY`. ✅

**XMPP compose** (`infra/compose/xmpp.yaml`): Maps `PROSODY_DOMAIN=${XMPP_DOMAIN}`. Root .env has `XMPP_DOMAIN=atl.chat`. ✅

**prepare-config.sh**: Sets `PROSODY_DOMAIN` from `XMPP_DOMAIN` when unset; sets `IRC_TLS_VERIFY` from `BRIDGE_IRC_TLS_VERIFY` or `ATL_ENVIRONMENT`. ✅

---

## Fixes applied

1. **init.sh** — `env.example` → `.env.example`
2. **config.example.yaml** — Added `irc_tls_verify: true`
3. **apps/web/.env.example** — `NEXT_PUBLIC_IRC_WEBSOCKET_URL` → `NEXT_PUBLIC_IRC_WS_URL`
4. **Docs** — CONFIG.md, DEVELOPMENT.md updated to `.env.example`
