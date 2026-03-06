"""Configuration: YAML + env overlay (AUDIT §5)."""

from bridge.config.loader import (
    _deep_update,
    load_config,
    load_config_with_env,
    validate_config,
)
from bridge.config.schema import Config, DiscordConfig, IRCConfig, XMPPConfig, cfg

__all__ = [
    "Config",
    "DiscordConfig",
    "IRCConfig",
    "XMPPConfig",
    "_deep_update",
    "cfg",
    "load_config",
    "load_config_with_env",
    "validate_config",
]
