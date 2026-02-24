# Scripts

> Scope: `scripts/` — inherits [AGENTS.md](../AGENTS.md).

Orchestration and config-generation scripts. Run via `just init` or manually.

## Files

| File | Purpose |
|------|---------|
| `init.sh` | Create data/ dirs, run prepare-config, generate dev certs |
| `prepare-config.sh` | Substitute `.env` into config templates (UnrealIRCd, Atheme, Bridge) |
| `gencloak-update-env.sh` | Generate cloak keys, update .env |
| `cert-manager/` | Lego/cert-manager helpers |

## Usage

- `just init` — runs `./scripts/init.sh`
- `./scripts/prepare-config.sh` — after editing `.env`
- `just irc gencloak` — runs `gencloak-update-env.sh`

## Related

- [Monorepo AGENTS.md](../AGENTS.md)
- [docs/infra/](../docs/infra/)
