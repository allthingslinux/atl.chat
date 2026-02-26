# Prosody XMPP Configuration Audit Report

**Date:** 2026-02-26
**Auditor:** Cloud Agent (manual wiki + modules.prosody.im review)
**Local config:** `apps/prosody/config/prosody.cfg.lua`
**References:** prosody.im/doc (configure, security, certificates, ports, modules, storage, mod_mam, mod_http_file_share, mod_muc) + modules.prosody.im (mod_anti_spam, mod_cloud_notify, mod_muc_limits, mod_http_admin_api, mod_firewall)

---

## Findings

### 🔴 CRITICAL — Insecure `.env.example` defaults for TLS/auth

The `.env.example` ships with:

```
PROSODY_C2S_REQUIRE_ENCRYPTION=false
PROSODY_S2S_REQUIRE_ENCRYPTION=false
PROSODY_S2S_SECURE_AUTH=false
PROSODY_ALLOW_UNENCRYPTED_PLAIN_AUTH=true
```

The Prosody Security docs state:

- `c2s_require_encryption` should be **true** (default in Prosody). "Almost all clients will use SSL/TLS out of the box."
- `s2s_require_encryption` should be **true** (default in Prosody). "By default Prosody requires encrypted server-to-server connections."
- `s2s_secure_auth` should be **true** for strong authentication. With `false`, Prosody falls back to DNS dialback which is weaker.
- `allow_unencrypted_plain_auth = true` allows plaintext passwords over unencrypted connections — a serious security risk.

**Fix:** Change `.env.example` defaults to secure values. Move insecure overrides to `.env.dev.example` for local development only.

### 🔴 CRITICAL — Global `ssl` block is commented out

Lines 531-536 have the TLS configuration entirely commented out:

```lua
-- ssl = {
-- protocol = "tlsv1_2+",
-- ciphers = "ECDHE+AESGCM:ECDHE+CHACHA20:...",
-- curve = "secp384r1",
-- options = { "cipher_server_preference", "single_dh_use", "single_ecdh_use" },
-- }
```

This means Prosody uses its built-in defaults. While Prosody's defaults are reasonable, the Security docs recommend explicitly configuring TLS for production. The commented config shows good settings — they should be enabled.

**Fix:** Uncomment the global `ssl` block.

### 🟡 WARNING — `legacyauth` module enabled

Line 18 loads `legacyauth`:

```lua
"legacyauth", -- Legacy authentication. Only used by some old clients and bots.
```

The Prosody docs describe this as supporting only "some old clients and bots." For a modern XMPP deployment with SCRAM-SHA-256 SASL auth, legacy auth is unnecessary and widens the attack surface.

**Fix:** Comment out or remove `legacyauth` unless specific legacy clients require it.

### 🟡 WARNING — `http_status_allow_cidr = "0.0.0.0/0"` (world-open)

Line 446:

```lua
http_status_allow_cidr = "0.0.0.0/0"
```

This exposes the HTTP status monitoring endpoint to the entire internet. While the status page itself may not contain sensitive data, it leaks server operational information to potential attackers.

**Fix:** Restrict to Docker network and localhost:

```lua
http_status_allow_cidr = "172.16.0.0/12"
```

### 🟡 WARNING — `archive_expires_after` defaults differ from upstream

The config defaults to `"1y"` (1 year) if the env var is not set:

```lua
archive_expires_after = ... or "1y"
```

The Prosody MAM docs state the default is `"1w"` (1 week). While 1 year is a valid choice for a community server, it should be a deliberate decision, and the storage implications should be considered (SQLite with 1 year of archives for many users will grow large).

**Status:** Acknowledged as intentional, but ensure monitoring is in place for database size.

### 🟡 WARNING — `max_connections_per_ip` may be too restrictive

Line 517:

```lua
max_connections_per_ip = ... or 5
```

The default of 5 per IP is fine for individual users, but in a Docker environment where the bridge and other services connect from the same IP, this could be restrictive. The bridge container shares the Docker network.

**Fix:** Consider increasing for Docker IPs or ensure the bridge connects from a recognizable IP that's exempted.

### 🟢 OK — Module selection comprehensive and modern

The config loads an excellent set of modules covering:

- Core protocol (roster, saslauth, tls, dialback, disco, presence, message, iq)
- Modern messaging (mam, carbons, smacks, offline)
- Mobile optimization (csi, csi_battery_saver, cloud_notify)
- Security (blocklist, anti_spam, spam_reporting, report_forward, admin_blocklist, mimicking, tombstones)
- XMPP compliance (server_contact_info, server_info, compliance_latest)
- Web services (http, bosh, websocket, conversejs, http_files)
- S2S enhancements (s2s_bidi, s2s_keepalive, s2s_status)

This exceeds typical Prosody deployments and covers XEP compliance well.

### 🟢 OK — Authentication properly configured

```lua
authentication = "internal_hashed"
sasl_mechanisms = { "SCRAM-SHA-256", "SCRAM-SHA-1" }
```

Uses hashed storage (as recommended by Security docs) with modern SCRAM-SHA-256 as primary mechanism. SCRAM-SHA-1 kept for compatibility.

### 🟢 OK — Anti-spam with xmppbl.org RTBL

```lua
anti_spam_services = { "xmppbl.org" }
```

Matches the mod_anti_spam docs recommendation for subscribing to shared block lists.

### 🟢 OK — Push notification privacy settings

```lua
push_notification_with_body = false
push_notification_with_sender = false
```

Matches mod_cloud_notify docs: "Not recommended" to enable these due to privacy implications. The config correctly keeps them disabled.

### 🟢 OK — Rate limiting properly configured

The `limits` block with c2s, s2s, and http_upload rate limits is well-structured and uses env vars for customization.

### 🟢 OK — MUC limits match upstream defaults

All `muc_limits` settings match the module defaults exactly (muc_event_rate=0.5, muc_burst_factor=6, etc.).

### 🟢 OK — HTTP security headers

The `http_headers` block includes HSTS, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy, and Content-Security-Policy. This is excellent and exceeds typical XMPP deployments.

### 🟢 OK — TURN/STUN external configuration

Properly configured with shared secret, hostname, ports, TTL, and TCP support.

### 🟢 OK — Storage backend assignments

Comprehensive storage mapping with SQL for persistent data and memory for ephemeral data (caps, carbons). Correct pattern.

### 🟢 OK — Certificate handling in docker-entrypoint.sh

Thorough certificate setup with Let's Encrypt layout, legacy fallback, and self-signed generation. HTTPS service discovery symlinks properly created.

### 🟢 OK — Trusted proxies

```lua
trusted_proxies = { "127.0.0.1", "172.16.0.0/12", "10.0.0.0/8" }
```

Covers localhost and Docker networks.

### 💡 SUGGESTION — Consider enabling `mod_register` for password changes

Line 75 disables register entirely:

```lua
-- "register", -- Password changes (XEP-0077); registration disabled
```

While self-registration should stay disabled (Portal provisions), `mod_register` is also needed for **password changes** by existing users. Consider enabling it with `allow_registration = false` to allow password changes without self-registration.

### 💡 SUGGESTION — Consider `dont_archive_namespaces`

Lines 200-203 have sensible namespace exclusions commented out:

```lua
-- dont_archive_namespaces = {
--   "http://jabber.org/protocol/chatstates",
--   "urn:xmpp:jingle-message:0",
-- }
```

Enabling these would reduce archive storage by excluding chat state notifications (typing indicators) and Jingle call signaling.

### 💡 SUGGESTION — Enable `mod_log_slow_events`

The module is listed in `modules.list` (line 30) but not in `modules_enabled`. This module helps identify performance bottlenecks.

### 💡 SUGGESTION — Enable `mod_reload_modules`

Listed in `modules.list` (line 32) but not enabled. Allows modules to be reloaded on config change without full restart.

---

## Summary

| Severity | Count | Key Items |
|----------|-------|-----------|
| 🔴 CRITICAL | 2 | Insecure `.env.example` TLS/auth defaults; global ssl block commented out |
| 🟡 WARNING | 3 | legacyauth enabled; http_status world-open; MAM retention vs upstream |
| 🟢 OK | 12+ | Module selection, auth, anti-spam, push privacy, rate limits, MUC limits, HTTP headers, TURN, storage, certs, proxies |
| 💡 SUGGESTION | 4 | mod_register for password changes, dont_archive_namespaces, mod_log_slow_events, mod_reload_modules |

### Overall Assessment

The Prosody configuration is **excellent** for a Docker-deployed XMPP server. The module selection is comprehensive and modern, covering XMPP compliance, mobile optimization, spam prevention, and web services. The main issues are the insecure `.env.example` defaults and the commented-out global TLS block — both straightforward to fix. The HTTP security headers, rate limiting, and storage configuration all follow best practices.
