"""Config schema and accessor (AUDIT §2)."""

from __future__ import annotations

import os
from typing import Any

from loguru import logger

from bridge.core.errors import BridgeConfigurationError

# Env keys that override config (centralized; loaded once per reload)
_ENV_OVERRIDE_KEYS = (
    "BRIDGE_IRC_REDACT_ENABLED",
    "BRIDGE_RELAYMSG_CLEAN_NICKS",
    "BRIDGE_IRC_TLS_VERIFY",
    "ATL_ENVIRONMENT",
)


def _load_env_overrides() -> dict[str, str]:
    """Load env overrides once per reload (AUDIT §3.5)."""
    return {k: os.environ.get(k, "") for k in _ENV_OVERRIDE_KEYS}


def _parse_bool_env(val: str) -> bool | None:
    """Parse env string to bool; None if not a recognized bool."""
    v = val.lower()
    if v in ("1", "true", "yes"):
        return True
    if v in ("0", "false", "no"):
        return False
    return None


class Config:
    """Config accessor with attribute-style access for nested keys."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = data or {}
        self._env: dict[str, str] = _load_env_overrides()

    def reload(self, data: dict[str, Any], *, validate: bool = True) -> None:
        """Replace config data (e.g. on SIGHUP reload)."""
        self._data = data or {}
        self._env = _load_env_overrides()
        if validate:
            self._validate()
        mappings_count = len(self.mappings)
        logger.debug("Config reloaded: {} mappings", mappings_count)

    def _validate(self) -> None:
        """Validate config structure; raise BridgeConfigurationError on failure."""
        mappings = self._data.get("mappings")
        if mappings is not None and not isinstance(mappings, list):
            raise BridgeConfigurationError(
                "mappings must be a list",
                code="invalid_mappings",
                details={"type": type(mappings).__name__},
            )
        for i, item in enumerate(self.mappings):
            if not isinstance(item, dict):
                raise BridgeConfigurationError(
                    f"mappings[{i}] must be a dict",
                    code="invalid_mapping_item",
                    details={"index": i},
                )
            if not item.get("discord_channel_id"):
                raise BridgeConfigurationError(
                    f"mappings[{i}] missing discord_channel_id",
                    code="missing_discord_channel_id",
                    details={"index": i},
                )

    @property
    def raw(self) -> dict[str, Any]:
        """Raw config dict for gateway/router."""
        return self._data

    def get(self, key: str, default: Any = None) -> Any:
        """Get value by dot-separated path."""
        parts = key.split(".")
        obj: Any = self._data
        for part in parts:
            if isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                return default
        return obj

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        return key in self._data

    @property
    def mappings(self) -> list[dict[str, Any]]:
        """Channel mapping list."""
        m = self._data.get("mappings")
        return m if isinstance(m, list) else []

    @property
    def announce_joins_and_quits(self) -> bool:
        return bool(self._data.get("announce_joins_and_quits", True))

    @property
    def announce_extras(self) -> bool:
        return bool(self._data.get("announce_extras", False))

    @property
    def identity_cache_ttl_seconds(self) -> int:
        return int(self._data.get("identity_cache_ttl_seconds", 3600))

    @property
    def avatar_cache_ttl_seconds(self) -> int:
        return int(self._data.get("avatar_cache_ttl_seconds", 86400))

    @property
    def xmpp_avatar_base_url(self) -> str | None:
        val = self._data.get("xmpp_avatar_base_url")
        if val and isinstance(val, str) and val.strip():
            return val.strip()
        return None

    @property
    def irc_puppet_idle_timeout_hours(self) -> int:
        return int(self._data.get("irc_puppet_idle_timeout_hours", 24))

    @property
    def irc_puppet_postfix(self) -> str:
        return str(self._data.get("irc_puppet_postfix", ""))

    @property
    def irc_throttle_limit(self) -> int:
        return int(self._data.get("irc_throttle_limit", 10))

    @property
    def irc_message_queue(self) -> int:
        return int(self._data.get("irc_message_queue", 30))

    @property
    def irc_rejoin_delay(self) -> float:
        return float(self._data.get("irc_rejoin_delay", 5))

    @property
    def irc_auto_rejoin(self) -> bool:
        return bool(self._data.get("irc_auto_rejoin", True))

    @property
    def irc_redact_enabled(self) -> bool:
        env_val = self._env.get("BRIDGE_IRC_REDACT_ENABLED", "")
        parsed = _parse_bool_env(env_val)
        if parsed is not None:
            return parsed
        return bool(self._data.get("irc_redact_enabled", False))

    @property
    def irc_relaymsg_clean_nicks(self) -> bool:
        env_val = self._env.get("BRIDGE_RELAYMSG_CLEAN_NICKS", "")
        if _parse_bool_env(env_val) is True:
            return True
        return bool(self._data.get("irc_relaymsg_clean_nicks", False))

    @property
    def irc_tls_verify(self) -> bool:
        env_val = self._env.get("BRIDGE_IRC_TLS_VERIFY", "")
        parsed = _parse_bool_env(env_val)
        if parsed is not None:
            return parsed
        if self._env.get("ATL_ENVIRONMENT") == "dev":
            return bool(self._data.get("irc_tls_verify", False))
        return bool(self._data.get("irc_tls_verify", True))

    @property
    def irc_use_sasl(self) -> bool:
        return bool(self._data.get("irc_use_sasl", False))

    @property
    def irc_sasl_user(self) -> str:
        return str(self._data.get("irc_sasl_user", ""))

    @property
    def irc_sasl_password(self) -> str:
        return str(self._data.get("irc_sasl_password", ""))

    @property
    def irc_puppet_ping_interval(self) -> int:
        return int(self._data.get("irc_puppet_ping_interval", 120))

    @property
    def irc_puppet_prejoin_commands(self) -> list[str]:
        val = self._data.get("irc_puppet_prejoin_commands")
        if isinstance(val, list):
            return [str(c) for c in val]
        return []

    @property
    def content_filter_regex(self) -> list[str]:
        val = self._data.get("content_filter_regex")
        if isinstance(val, list):
            return [str(p) for p in val]
        return []


cfg: Config = Config({})
