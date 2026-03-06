"""Config schema and accessor (AUDIT §2)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
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


# ---------------------------------------------------------------------------
# Nested protocol-specific config dataclasses (Design D4)
# ---------------------------------------------------------------------------


@dataclass
class IRCConfig:
    """IRC-specific behavioral settings. Connection credentials come from env vars."""

    puppet_idle_timeout_hours: int = 24
    puppet_postfix: str = ""
    throttle_limit: int = 10
    message_queue: int = 30
    rejoin_delay: float = 5
    auto_rejoin: bool = True
    use_sasl: bool = False
    sasl_user: str = ""
    sasl_password: str = ""
    redact_enabled: bool = False
    relaymsg_clean_nicks: bool = False
    tls_verify: bool = True
    puppet_ping_interval: int = 120
    puppet_prejoin_commands: list[str] = field(default_factory=list)


@dataclass
class XMPPConfig:
    """XMPP-specific behavioral settings. Connection credentials come from env vars."""

    avatar_base_url: str | None = None
    avatar_public_url: str | None = None
    auto_rejoin: bool = True


@dataclass
class DiscordConfig:
    """Discord-specific config. Connection token comes from DISCORD_TOKEN env var."""

    webhook_cache_ttl: int = 86400
    max_webhooks_per_channel: int = 15
    typing_throttle_seconds: float = 3.0
    queue_consumer_delay: float = 0.25


# ---------------------------------------------------------------------------
# Helper: build nested dataclass from flat dict + env overrides
# ---------------------------------------------------------------------------


def _build_irc_config(data: dict[str, Any], env: dict[str, str]) -> IRCConfig:
    """Build IRCConfig from flat config dict, applying env overrides."""
    # Start with values from the raw dict (flat keys prefixed with irc_)
    kw: dict[str, Any] = {}
    kw["puppet_idle_timeout_hours"] = int(data.get("irc_puppet_idle_timeout_hours", 24))
    kw["puppet_postfix"] = str(data.get("irc_puppet_postfix", ""))
    kw["throttle_limit"] = int(data.get("irc_throttle_limit", 10))
    kw["message_queue"] = int(data.get("irc_message_queue", 30))
    kw["rejoin_delay"] = float(data.get("irc_rejoin_delay", 5))
    kw["auto_rejoin"] = bool(data.get("irc_auto_rejoin", True))
    kw["use_sasl"] = bool(data.get("irc_use_sasl", False))
    kw["sasl_user"] = str(data.get("irc_sasl_user", ""))
    kw["sasl_password"] = str(data.get("irc_sasl_password", ""))
    kw["puppet_ping_interval"] = int(data.get("irc_puppet_ping_interval", 120))

    val = data.get("irc_puppet_prejoin_commands")
    kw["puppet_prejoin_commands"] = [str(c) for c in val] if isinstance(val, list) else []

    # --- env overrides for redact_enabled ---
    env_redact = env.get("BRIDGE_IRC_REDACT_ENABLED", "")
    parsed = _parse_bool_env(env_redact)
    if parsed is not None:
        kw["redact_enabled"] = parsed
    else:
        kw["redact_enabled"] = bool(data.get("irc_redact_enabled", False))

    # --- env overrides for relaymsg_clean_nicks ---
    env_clean = env.get("BRIDGE_RELAYMSG_CLEAN_NICKS", "")
    if _parse_bool_env(env_clean) is True:
        kw["relaymsg_clean_nicks"] = True
    else:
        kw["relaymsg_clean_nicks"] = bool(data.get("irc_relaymsg_clean_nicks", False))

    # --- env overrides for tls_verify ---
    env_tls = env.get("BRIDGE_IRC_TLS_VERIFY", "")
    parsed_tls = _parse_bool_env(env_tls)
    if parsed_tls is not None:
        kw["tls_verify"] = parsed_tls
    elif env.get("ATL_ENVIRONMENT") == "dev":
        kw["tls_verify"] = bool(data.get("irc_tls_verify", False))
    else:
        kw["tls_verify"] = bool(data.get("irc_tls_verify", True))

    return IRCConfig(**kw)


def _build_xmpp_config(data: dict[str, Any]) -> XMPPConfig:
    """Build XMPPConfig from flat config dict."""
    base = data.get("xmpp_avatar_base_url")
    public = data.get("xmpp_avatar_public_url")
    return XMPPConfig(
        avatar_base_url=base.strip() if isinstance(base, str) and base and base.strip() else None,
        avatar_public_url=public.strip() if isinstance(public, str) and public and public.strip() else None,
        auto_rejoin=bool(data.get("xmpp_auto_rejoin", True)),
    )


def _build_discord_config(data: dict[str, Any]) -> DiscordConfig:
    """Build DiscordConfig from flat config dict."""
    return DiscordConfig(
        webhook_cache_ttl=int(data.get("discord_webhook_cache_ttl", 86400)),
        max_webhooks_per_channel=int(data.get("discord_max_webhooks_per_channel", 15)),
        typing_throttle_seconds=float(data.get("discord_typing_throttle_seconds", 3.0)),
        queue_consumer_delay=float(data.get("discord_queue_consumer_delay", 0.25)),
    )


# ---------------------------------------------------------------------------
# Top-level Config — backward-compatible with flat @property access
# ---------------------------------------------------------------------------


class Config:
    """Config accessor with nested sub-configs and backward-compatible flat access."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = data or {}
        self._env: dict[str, str] = _load_env_overrides()
        self._build_nested()

    def _build_nested(self) -> None:
        """(Re)build nested sub-config dataclasses from _data and _env."""
        self.irc: IRCConfig = _build_irc_config(self._data, self._env)
        self.xmpp: XMPPConfig = _build_xmpp_config(self._data)
        self.discord: DiscordConfig = _build_discord_config(self._data)

    def reload(self, data: dict[str, Any], *, validate: bool = True) -> None:
        """Replace config data (e.g. on SIGHUP reload)."""
        self._data = data or {}
        self._env = _load_env_overrides()
        self._build_nested()
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

    # ------------------------------------------------------------------
    # Generic accessors (unchanged)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Top-level properties
    # ------------------------------------------------------------------

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
    def content_filter_regex(self) -> list[str]:
        val = self._data.get("content_filter_regex")
        if isinstance(val, list):
            return [str(p) for p in val]
        return []

    @property
    def paste_service_url(self) -> str | None:
        """URL of paste service for code block uploads."""
        val = self._data.get("paste_service_url")
        if val and isinstance(val, str) and val.strip():
            return val.strip()
        return None

    @property
    def remote_nick_format(self) -> str:
        """Template for remote nick formatting (default: '<{nick}> '). Supports {nick} and {protocol}."""
        val = self._data.get("remote_nick_format")
        if val is not None and isinstance(val, str):
            return val
        return "<{nick}> "

    @property
    def edit_suffix(self) -> str:
        """Suffix appended to edited messages on protocols without native edit support (default: ' (edited)')."""
        val = self._data.get("edit_suffix")
        if val is not None and isinstance(val, str):
            return val
        return " (edited)"

    # ------------------------------------------------------------------
    # Backward-compatible flat IRC properties (delegate to self.irc)
    # ------------------------------------------------------------------

    @property
    def irc_puppet_idle_timeout_hours(self) -> int:
        return self.irc.puppet_idle_timeout_hours

    @property
    def irc_puppet_postfix(self) -> str:
        return self.irc.puppet_postfix

    @property
    def irc_throttle_limit(self) -> int:
        return self.irc.throttle_limit

    @property
    def irc_message_queue(self) -> int:
        return self.irc.message_queue

    @property
    def irc_rejoin_delay(self) -> float:
        return self.irc.rejoin_delay

    @property
    def irc_auto_rejoin(self) -> bool:
        return self.irc.auto_rejoin

    @property
    def irc_use_sasl(self) -> bool:
        return self.irc.use_sasl

    @property
    def irc_sasl_user(self) -> str:
        return self.irc.sasl_user

    @property
    def irc_sasl_password(self) -> str:
        return self.irc.sasl_password

    @property
    def irc_redact_enabled(self) -> bool:
        return self.irc.redact_enabled

    @property
    def irc_relaymsg_clean_nicks(self) -> bool:
        return self.irc.relaymsg_clean_nicks

    @property
    def irc_tls_verify(self) -> bool:
        return self.irc.tls_verify

    @property
    def irc_puppet_ping_interval(self) -> int:
        return self.irc.puppet_ping_interval

    @property
    def irc_puppet_prejoin_commands(self) -> list[str]:
        return self.irc.puppet_prejoin_commands

    # ------------------------------------------------------------------
    # Backward-compatible flat XMPP properties (delegate to self.xmpp)
    # ------------------------------------------------------------------

    @property
    def xmpp_avatar_base_url(self) -> str | None:
        return self.xmpp.avatar_base_url

    @property
    def xmpp_avatar_public_url(self) -> str | None:
        return self.xmpp.avatar_public_url

    @property
    def xmpp_auto_rejoin(self) -> bool:
        return self.xmpp.auto_rejoin


cfg: Config = Config({})
