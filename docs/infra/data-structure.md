# Data Directory Structure

Canonical layout for `data/` (source of truth: `scripts/init.sh` + `infra/compose/`).

## Canonical Layout

```
data/
├── irc/
│   ├── data/          # UnrealIRCd: rpc.socket, services.sock, runtime data
│   ├── logs/          # UnrealIRCd logs
│   └── webpanel-data/ # Webpanel persistent data
├── atheme/
│   ├── data/          # Atheme SQLite: services.db
│   └── logs/          # Atheme logs (atheme/atheme.log)
├── xmpp/
│   ├── data/          # Prosody: prosody.sqlite
│   └── uploads/       # Prosody file uploads
└── certs/             # Certificates
    ├── certificates/  # Lego output (prod: _.domain.crt, _.domain.key)
    ├── accounts/      # Lego ACME account data
    └── live/          # Service layout: live/<domain>/fullchain.pem, privkey.pem
       ├── irc.localhost/   # Dev
       └── irc.atl.chat/   # Prod (or copied from Lego)
```

## Obsolete Paths (Do Not Use)

| Obsolete           | Use Instead     |
|--------------------|-----------------|
| `data/unrealircd/` | `data/irc/data/` |
| `data/letsencrypt/`| `data/certs/`   |
| `data/atheme/atheme.db` | `data/atheme/data/services.db` |
| `logs/atheme/`     | `data/atheme/logs/` |
| `logs/atl-irc-server/` | `data/irc/logs/` |
| `data/docs/`       | Not used; remove if present |

**Cleanup:** Remove obsolete dirs manually (e.g. `rm -rf data/unrealircd data/letsencrypt data/docs`) if they exist from older setups.

## Compose Volume Mapping

| Host Path                | Container Mount                          | Service   |
|--------------------------|------------------------------------------|-----------|
| `data/irc/data`          | `/home/unrealircd/unrealircd/data`       | UnrealIRCd|
| `data/irc/logs`          | `/home/unrealircd/unrealircd/logs`       | UnrealIRCd|
| `data/irc/webpanel-data` | `/var/www/html/unrealircd-webpanel/data` | Webpanel  |
| `data/atheme/data`       | `/usr/local/atheme/data`                 | Atheme    |
| `data/atheme/logs`       | `/usr/local/atheme/logs`                 | Atheme    |
| `data/xmpp/data`         | `/var/lib/prosody/data`                  | Prosody   |
| `data/xmpp/uploads`       | `/var/lib/prosody/uploads`               | Prosody   |
| `data/certs`             | `/home/unrealircd/unrealircd/certs` (ro) | UnrealIRCd|
| `data/certs`             | `/etc/prosody/certs`                     | Prosody   |
