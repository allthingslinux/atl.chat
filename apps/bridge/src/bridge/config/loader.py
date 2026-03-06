"""Config loading and validation (AUDIT §2)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bridge.config.schema import Config

import yaml
from loguru import logger

from bridge.core.errors import BridgeConfigurationError

# ---------------------------------------------------------------------------
# Field-type schema for validation.
# Each entry: (expected_type_tuple, default_value)
# None as default means the field is optional with no default (str | None).
# ---------------------------------------------------------------------------

_FIELD_SCHEMA: dict[str, tuple[tuple[type, ...], Any]] = {
    # Top-level
    "mappings": ((list,), []),
    "announce_joins_and_quits": ((bool,), True),
    "announce_extras": ((bool,), False),
    "identity_cache_ttl_seconds": ((int,), 3600),
    "avatar_cache_ttl_seconds": ((int,), 86400),
    "content_filter_regex": ((list,), []),
    "paste_service_url": ((str,), None),
    "remote_nick_format": ((str,), "<{nick}> "),
    "edit_suffix": ((str,), " (edited)"),
    # IRC
    "irc_puppet_idle_timeout_hours": ((int,), 24),
    "irc_puppet_postfix": ((str,), ""),
    "irc_throttle_limit": ((int,), 10),
    "irc_message_queue": ((int,), 30),
    "irc_rejoin_delay": ((int, float), 5),
    "irc_auto_rejoin": ((bool,), True),
    "irc_use_sasl": ((bool,), False),
    "irc_sasl_user": ((str,), ""),
    "irc_sasl_password": ((str,), ""),
    "irc_redact_enabled": ((bool,), False),
    "irc_relaymsg_clean_nicks": ((bool,), False),
    "irc_tls_verify": ((bool,), True),
    "irc_puppet_ping_interval": ((int,), 120),
    "irc_puppet_prejoin_commands": ((list,), []),
    # Discord
    "discord_webhook_cache_ttl": ((int,), 86400),
    "discord_max_webhooks_per_channel": ((int,), 15),
    "discord_typing_throttle_seconds": ((int, float), 3.0),
    "discord_queue_consumer_delay": ((int, float), 0.25),
    # XMPP
    "xmpp_avatar_base_url": ((str,), None),
    "xmpp_avatar_public_url": ((str,), None),
    "xmpp_auto_rejoin": ((bool,), True),
}


def _deep_update(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_update(result[key], value)
        else:
            result[key] = value
    return result


def _validate_field_types(data: dict[str, Any]) -> list[str]:
    """Validate field types against _FIELD_SCHEMA. Returns list of error messages."""
    errors: list[str] = []
    for key, (expected_types, _default) in _FIELD_SCHEMA.items():
        if key not in data:
            continue
        value = data[key]
        if value is None:
            # None is acceptable for optional fields (str | None defaults)
            continue
        # Python bool is a subclass of int, so check bool fields first
        if bool in expected_types and not isinstance(value, bool) and isinstance(value, int):
            # int provided where bool expected — coerce silently
            continue
        if not isinstance(value, expected_types):
            type_names = "/".join(t.__name__ for t in expected_types)
            errors.append(f"field '{key}' expected {type_names}, got {type(value).__name__}")
    return errors


def validate_config(data: dict[str, Any]) -> Config:
    """Validate a raw config dict and return a populated Config instance.

    Validates field types against the schema, raises BridgeConfigurationError
    on type mismatches, and delegates to Config (which handles defaults and
    nested dataclass construction).
    """
    from bridge.config.schema import Config

    if not isinstance(data, dict):
        raise BridgeConfigurationError(
            "config must be a dict",
            code="invalid_config_type",
            details={"type": type(data).__name__},
        )

    errors = _validate_field_types(data)
    if errors:
        raise BridgeConfigurationError(
            f"config validation failed: {'; '.join(errors)}",
            code="invalid_field_types",
            details={"errors": errors},
        )

    cfg = Config(data)
    cfg._validate()
    return cfg


def load_config(path: str | Path) -> dict[str, Any]:
    """Load config from YAML file. Use SafeLoader. Returns raw dict."""
    path = Path(path)
    if not path.exists():
        logger.warning("Config file not found: {}", path)
        return {}

    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            logger.warning("Config file {} has invalid structure (expected dict)", path)
            return {}
        return data
    except yaml.YAMLError as exc:
        logger.error("Failed to parse config {}: {}", path, exc)
        raise


def load_config_with_env(path: str | Path) -> dict[str, Any]:
    """Load config from YAML and overlay env-derived values."""
    from dotenv import load_dotenv

    load_dotenv()
    return load_config(path)
