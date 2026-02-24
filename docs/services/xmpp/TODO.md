# XMPP (Prosody) – Follow-up Items

Investigation items from Prosody documentation audits. Not blocking; review when time permits.

## mod_bosh

- [ ] **Extra BOSH options** – Verify `bosh_max_polling`, `bosh_session_timeout`, `bosh_hold_timeout`, `bosh_window` against Prosody docs (may be from another module/version)
- [ ] **consider_bosh_secure** – Set to `true` if nginx terminates TLS and proxies BOSH over HTTP to Prosody; leave `false` if proxying HTTPS→HTTPS

## Components

- [ ] **component_interfaces** – Confirm bridge connectivity; default loopback may block atl-bridge. Add `component_interfaces = { "*" }` if bridge cannot connect from its container

## mod_blocklist

- [ ] **Optional config** – Review `bounce_blocked_messages` and `blocklist_cache_size` if tuning blocklist behavior

## mod_mam

- [ ] **archive_compression** – Verify against Prosody docs; present in config but not in mod_mam option table (may be from newer version)

## mod_muc_cache_media

- [ ] **mod_muc_cache_media** – Cache MUC media (OOB, SIMS) locally to avoid privacy leaks (sender domains). Requires Prosody 13+, `muc_media_store_path`, `muc_media_public_base`, `muc_media_max_size`. Does not use Prosody HTTP; requires external static file serving (e.g. nginx). When message is moderated, cached media is deleted. [modules.prosody.im/mod_muc_cache_media](https://modules.prosody.im/mod_muc_cache_media.html)

## mod_register_json (web-form registration)

- [ ] **mod_register_json** – Community module for web-form registration via POST + Base64 JSON. Requires `reg_servlet_auth_token`. Verification path: `/base-path/verify/`. Pair with `mod_register_redirect` to restrict registration to webform only. Alternative to Portal provisioning if self-registration with email verification is needed. [modules.prosody.im/mod_register_json](https://modules.prosody.im/mod_register_json.html)

## Public servers (if open registration)

- [ ] **min_seconds_between_registrations** – Add per-IP rate limit (e.g. 60–300s)
- [x] **mod_muc_limits** – Add community module for MUC flooding prevention
- [ ] **mod_firewall** – Add community module for rule-based stanza filtering
- [ ] **mod_limits tuning** – Consider stricter c2s limits if abuse occurs

## mod_net_proxy

- [ ] **mod_net_proxy** – Research PROXY protocol (v1/v2) for c2s/s2s when fronted by HAProxy or similar. Requires separate ports (e.g. 15222→c2s, 15269→s2s), `proxy_trusted_proxies`, optional `proxy_out` for outgoing s2s via proxy. Enables real client IP preservation when load balancer terminates TCP. Do not expose PROXY ports to internet. [modules.prosody.im/mod_net_proxy](https://modules.prosody.im/mod_net_proxy.html)

## mod_rest

- [ ] **mod_rest** – RESTful API for sending/receiving XMPP stanzas via HTTP. For bots and HTTP-based components. Install on VirtualHost (user auth) or as Component (Basic auth: JID + secret). Supports XML and JSON payloads, webhook callback for receiving stanzas. OAuth2 via mod_http_oauth2. Path: `/rest`. [modules.prosody.im/mod_rest](https://modules.prosody.im/mod_rest.html)

## Logging

- [ ] **Split logging** – Add `prosody.err` for error-only output
- [ ] **Custom timestamps** – Add `timestamps` option if needed (e.g. `"%s"` for Unix time)
