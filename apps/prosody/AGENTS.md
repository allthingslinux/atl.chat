# Prosody (XMPP)

> Scope: XMPP server app. Inherits monorepo [AGENTS.md](../../AGENTS.md).

Prosody XMPP server with Lua config. Loaded via root: `just xmpp`.

## Tech Stack

Prosody · Lua config · Docker · PostgreSQL (optional, for storage)

## Avatar Modules

- **mod_http_avatar** — Serves vCard avatars at `http://host:5280/avatar/<username>`. Used by bridge for XMPP→IRC/Discord avatar sync.
- **mod_pep_vcard_png_avatar** — Syncs PEP avatars to vCard and converts webp→PNG (Conversations compat). Replaces `mod_pep_vcard_avatar`. Requires `webp` package (dwebp) in container.

## Repository Structure

```
config/
└── prosody.cfg.lua    # Main Prosody config

www/                   # Static assets
Containerfile
docker-entrypoint.sh
justfile               # Loaded via: mod xmpp './apps/prosody'
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
- [docs/services/xmpp/](../../docs/services/xmpp/)
