"""Configuration: YAML + env overlay (AUDIT §5)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _deep_update(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_update(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | Path) -> dict[str, Any]:
    """Load config from YAML file. Use SafeLoader. Returns raw dict."""
    path = Path(path)
    if not path.exists():
        return {}

    with open(path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def load_config_with_env(path: str | Path) -> dict[str, Any]:
    """Load config from YAML and overlay env-derived values.

    Loads .env via python-dotenv when present (cwd or documented path).
    Process env overrides are applied by callers where needed.
    """
    from dotenv import load_dotenv

    load_dotenv()
    return load_config(path)


class Config:
    """Config accessor with attribute-style access for nested keys."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = data or {}

    def reload(self, data: dict[str, Any]) -> None:
        """Replace config data (e.g. on SIGHUP reload)."""
        self._data = data or {}

    @property
    def raw(self) -> dict[str, Any]:
        """Raw config dict for gateway/router."""
        return self._data

    def get(self, key: str, default: Any = None) -> Any:
        """Get value by dot-separated path (e.g. 'mappings.0.discord_channel_id')."""
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
        """Whether to relay join/part/quit/kick (AUDIT §5)."""
        return bool(self._data.get("announce_joins_and_quits", True))

    @property
    def announce_extras(self) -> bool:
        """Whether to relay topics/mode changes (AUDIT §5)."""
        return bool(self._data.get("announce_extras", False))

    @property
    def identity_cache_ttl_seconds(self) -> int:
        """TTL for identity cache in seconds."""
        return int(self._data.get("identity_cache_ttl_seconds", 3600))

    @property
    def avatar_cache_ttl_seconds(self) -> int:
        """TTL for avatar URL cache in seconds."""
        return int(self._data.get("avatar_cache_ttl_seconds", 86400))

    @property
    def irc_puppet_idle_timeout_hours(self) -> int:
        """Hours before disconnecting idle IRC puppets (AUDIT §4)."""
        return int(self._data.get("irc_puppet_idle_timeout_hours", 24))

    @property
    def irc_puppet_postfix(self) -> str:
        """Optional postfix for IRC puppet nicks (e.g. '|d')."""
        return str(self._data.get("irc_puppet_postfix", ""))

    @property
    def irc_throttle_limit(self) -> int:
        """IRC messages per second (token bucket limit)."""
        return int(self._data.get("irc_throttle_limit", 10))

    @property
    def irc_message_queue(self) -> int:
        """Max IRC outbound message queue size."""
        return int(self._data.get("irc_message_queue", 30))

    @property
    def irc_rejoin_delay(self) -> float:
        """Seconds to wait before rejoin after KICK/disconnect."""
        return float(self._data.get("irc_rejoin_delay", 5))

    @property
    def irc_auto_rejoin(self) -> bool:
        """Whether to auto-rejoin channels after KICK/disconnect."""
        return bool(self._data.get("irc_auto_rejoin", True))

    @property
    def irc_use_sasl(self) -> bool:
        """Use SASL PLAIN for IRC authentication."""
        return bool(self._data.get("irc_use_sasl", False))

    @property
    def irc_sasl_user(self) -> str:
        """SASL username for IRC."""
        return str(self._data.get("irc_sasl_user", ""))

    @property
    def irc_sasl_password(self) -> str:
        """SASL password for IRC."""
        return str(self._data.get("irc_sasl_password", ""))

    @property
    def content_filter_regex(self) -> list[str]:
        """Regex patterns; messages matching any are not bridged."""
        val = self._data.get("content_filter_regex")
        if isinstance(val, list):
            return [str(p) for p in val]
        return []


# Global config instance (set by __main__)
cfg: Config = Config({})
