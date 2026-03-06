# Config

> Scope: `src/bridge/config/` -- inherits [Bridge AGENTS.md](../../../AGENTS.md).

YAML configuration loading with environment variable overlay and hot-reload support.

## Files

| File | Purpose |
|------|---------|
| `loader.py` | `load_config(path)` -- loads YAML file; `load_config_with_env(path)` -- loads YAML + dotenv overlay; `validate_config(data)` -- schema validation |
| `schema.py` | `Config` class (all bridge settings as properties); `cfg` module-level singleton; `Config.reload(data)` for SIGHUP hot-swap |

## Config Singleton

`cfg` is the global `Config` instance. Never instantiate a second `Config`. Call `cfg.reload(data)` on SIGHUP to hot-swap settings without restarting.

## Related

- [bridge/AGENTS.md](../AGENTS.md)
- [Bridge AGENTS.md](../../../AGENTS.md)
