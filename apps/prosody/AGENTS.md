# Prosody (XMPP)

> Scope: XMPP server app. Inherits monorepo [AGENTS.md](../../AGENTS.md).

Prosody XMPP server with Lua config. Loaded via root: `just xmpp`.

## Tech Stack

Prosody · Lua config · Docker · PostgreSQL (optional, for storage)

## Avatar Modules

- **mod_http_avatar** — Serves vCard avatars at `/avatar/<username>`.
- **mod_http_pep_avatar** — Serves PEP avatars at `/pep_avatar/<username>`. Used by bridge for XMPP→IRC/Discord. Requires users to set Avatar PEP node public.

## Repository Structure

```
config/
└── prosody.cfg.lua        # Main Prosody config

custom_plugins/
└── mod_pep_open_avatars.lua  # PEP avatar access control plugin

scripts/                   # (empty — reserved for future helpers)

www/                       # Static assets
├── index.html
├── robots.txt
├── security.txt
└── .well-known/
    ├── index.html
    └── security.txt

Containerfile
docker-entrypoint.sh
justfile                   # Loaded via: mod xmpp './apps/prosody'
modules.list
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `just xmpp shell` | Bash into Prosody container |
| `just xmpp reload` | Reload Prosody config |
| `just xmpp adduser [user]` | Add XMPP user |
| `just xmpp deluser [user]` | Delete XMPP user |
| `just xmpp db-backup` | Backup database |
| `just xmpp check` | Run all Prosody sanity checks (prosodyctl check) |
| `just xmpp audit <host>` | View full audit log for a host |
| `just xmpp audit-user <jid>` | View audit log for a specific user |
| `just xmpp audit-global <host>` | View host-wide audit events (not user-specific) |
| `just xmpp check-config` | Sanity checks on config file |
| `just xmpp check-certs` | Verify certificate config (prosodyctl check certs) |
| `just xmpp check-cert [domain]` | Check certificate for domain |
| `just xmpp check-connectivity` | Test external connectivity (observe.jabber.network) |
| `just xmpp check-disabled` | Report disabled VirtualHosts/Components |
| `just xmpp check-dns` | Verify DNS records (SRV, etc.) |
| `just xmpp check-features` | Check for missing/unconfigured features |
| `just xmpp check-turn [stun_server]` | Test TURN/mod_turn_external config |

## Related

- [Monorepo AGENTS.md](../../AGENTS.md)

## Portal Integration (mod_http_admin_api)

The [Portal](https://github.com/allthingslinux/portal) provisions XMPP accounts via `mod_http_admin_api`, which requires a Bearer token from `mod_tokenauth`.

### Generating a token

From the monorepo root:

```bash
just prosody-token
```

This uses `prosodyctl shell` to call `mod_tokenauth.create_grant()` + `create_token()` directly in Lua, bypassing the OAuth2 flow entirely. The token is non-expiring (grant and token both have nil TTL).

Set the output as `PROSODY_REST_TOKEN` in the portal's `.env`.

### How it works

`mod_http_admin_api` only accepts `Bearer` tokens — no Basic auth, no API keys. Prosody's `mod_http_oauth2` is the standard way to obtain tokens (via authorization_code or device_code grants), but for service-to-service auth the `prosodyctl shell` approach is simpler:

```
>local tk = prosody.hosts["xmpp.localhost"].modules.tokenauth
>local grant = tk.create_grant("admin@xmpp.localhost", "admin@xmpp.localhost", nil, {})
>local token = tk.create_token("admin@xmpp.localhost", grant, "prosody:operator", nil, "portal-api")
>print(token)
```

The `>` prefix escapes the prosodyctl shell sandbox to access the running server's Lua state.

### Portal env vars

| Variable | Example | Purpose |
|----------|---------|---------|
| `PROSODY_REST_URL` | `http://localhost:5280` | Prosody HTTP endpoint (host network) |
| `PROSODY_REST_TOKEN` | `secret-token:...` | Bearer token from `just prosody-token` |
| `XMPP_DOMAIN` | `xmpp.localhost` | XMPP domain for JID construction |
