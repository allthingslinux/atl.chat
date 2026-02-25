"""Configuration: YAML + env overlay (AUDIT §5)."""

from bridge.config.loader import _deep_update, load_config, load_config_with_env
from bridge.config.schema import Config, cfg

__all__ = ["Config", "_deep_update", "cfg", "load_config", "load_config_with_env"]
