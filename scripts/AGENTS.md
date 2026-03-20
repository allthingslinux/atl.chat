# Scripts

> Scope: `scripts/` — inherits [AGENTS.md](../AGENTS.md).

Orchestration and config-generation scripts. Run via `just init` or manually.

## Files

| File | Purpose |
|------|---------|
| `init.sh` | Create data/ dirs, run prepare-config, generate dev certs |
| `prepare-config.sh` | `envsubst` from `.env` / `.env.<ATL_INIT_MODE>` into UnrealIRCd and Atheme templates, bridge `config.template.yaml` → `config.yaml`, The Lounge `config.js.template` → `data/thelounge/config.js`; sets defaults for IRC/WebSocket/GeoIP, bridge, and Prosody-related exports used by those templates |
| `gencloak-update-env.sh` | Generate cloak keys, update .env |
| `download_references.py` | Download reference documentation for offline use |
| `cert-manager/run.sh` | Lego/cert-manager helper script |

## Usage

- `just init` — runs `./scripts/init.sh`
- `./scripts/prepare-config.sh` — after editing `.env`
- `just irc gencloak` — runs `gencloak-update-env.sh`

## Related

- [Monorepo AGENTS.md](../AGENTS.md)
