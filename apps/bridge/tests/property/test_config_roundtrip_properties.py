"""Property-based tests for config load round-trip (CP16).

**Validates: Requirement 13.5**

Property CP16: Config Load Round-Trip
  Loading a valid config dict and serializing back preserves all field values
  and defaults.
"""

from __future__ import annotations

import os
from unittest import mock

from bridge.config.schema import Config
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Strategies for generating valid config field values
# ---------------------------------------------------------------------------

# Mapping items must have a discord_channel_id (non-empty string).
_mapping_item = st.fixed_dictionaries(
    {"discord_channel_id": st.text(min_size=1, max_size=30, alphabet=st.characters(categories=("L", "N")))},
)
_mappings = st.lists(_mapping_item, min_size=1, max_size=5)

# Non-empty, non-whitespace-only strings for URL-like optional fields.
_nonempty_str = st.text(
    min_size=1,
    max_size=60,
    alphabet=st.characters(categories=("L", "N", "P", "S")),
).filter(lambda s: s.strip() != "")

_str_commands = st.lists(
    st.text(min_size=1, max_size=30, alphabet=st.characters(categories=("L", "N"))),
    max_size=5,
)

_filter_patterns = st.lists(
    st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L", "N"))),
    max_size=3,
)

# Positive ints for timeout/TTL fields.
_pos_int = st.integers(min_value=1, max_value=100_000)
_pos_float = st.floats(min_value=0.1, max_value=1000.0, allow_nan=False, allow_infinity=False)


def _valid_config_dict() -> st.SearchStrategy[dict]:
    """Strategy that produces a fully-populated, type-correct config dict."""
    return st.fixed_dictionaries(
        {
            "mappings": _mappings,
            "announce_joins_and_quits": st.booleans(),
            "announce_extras": st.booleans(),
            "identity_cache_ttl_seconds": _pos_int,
            "avatar_cache_ttl_seconds": _pos_int,
            "content_filter_regex": _filter_patterns,
            "paste_service_url": _nonempty_str,
            "remote_nick_format": st.just("<{nick}> ") | st.just("[{protocol}] {nick}: "),
            "edit_suffix": st.text(min_size=0, max_size=20),
            # IRC fields
            "irc_puppet_idle_timeout_hours": _pos_int,
            "irc_puppet_postfix": st.text(min_size=0, max_size=10),
            "irc_throttle_limit": _pos_int,
            "irc_message_queue": _pos_int,
            "irc_rejoin_delay": _pos_float,
            "irc_auto_rejoin": st.booleans(),
            "irc_use_sasl": st.booleans(),
            "irc_sasl_user": st.text(min_size=0, max_size=20),
            "irc_sasl_password": st.text(min_size=0, max_size=20),
            "irc_redact_enabled": st.booleans(),
            "irc_relaymsg_clean_nicks": st.booleans(),
            "irc_tls_verify": st.booleans(),
            "irc_puppet_ping_interval": _pos_int,
            "irc_puppet_prejoin_commands": _str_commands,
            # Discord fields
            "discord_webhook_cache_ttl": _pos_int,
            "discord_max_webhooks_per_channel": _pos_int,
            "discord_typing_throttle_seconds": _pos_float,
            "discord_queue_consumer_delay": _pos_float,
            # XMPP fields
            "xmpp_avatar_base_url": _nonempty_str,
            "xmpp_avatar_public_url": _nonempty_str,
            "xmpp_auto_rejoin": st.booleans(),
        },
    )


# Env vars that override IRC config fields — must be cleared for round-trip.
_ENV_OVERRIDES = (
    "BRIDGE_IRC_REDACT_ENABLED",
    "BRIDGE_RELAYMSG_CLEAN_NICKS",
    "BRIDGE_IRC_TLS_VERIFY",
    "ATL_ENVIRONMENT",
)


class TestConfigLoadRoundTrip:
    """**Validates: Requirement 13.5**"""

    @given(data=_valid_config_dict())
    @settings(max_examples=200)
    def test_config_round_trip_preserves_values(self, data: dict) -> None:
        """CP16: Loading a valid config dict and reading back all field values
        preserves the input values.

        **Validates: Requirement 13.5**
        """
        # Clear env overrides so dict values are used directly.
        clean_env = {k: "" for k in _ENV_OVERRIDES}
        with mock.patch.dict(os.environ, clean_env, clear=False):
            cfg = Config(data)

        # -- Top-level fields --
        assert cfg.mappings == data["mappings"]
        assert cfg.announce_joins_and_quits == data["announce_joins_and_quits"]
        assert cfg.announce_extras == data["announce_extras"]
        assert cfg.identity_cache_ttl_seconds == data["identity_cache_ttl_seconds"]
        assert cfg.avatar_cache_ttl_seconds == data["avatar_cache_ttl_seconds"]
        assert cfg.content_filter_regex == data["content_filter_regex"]
        assert cfg.remote_nick_format == data["remote_nick_format"]
        assert cfg.edit_suffix == data["edit_suffix"]

        # paste_service_url strips whitespace; our strategy guarantees non-empty after strip.
        assert cfg.paste_service_url == data["paste_service_url"].strip()

        # -- IRC fields (via backward-compatible flat properties) --
        assert cfg.irc_puppet_idle_timeout_hours == data["irc_puppet_idle_timeout_hours"]
        assert cfg.irc_puppet_postfix == data["irc_puppet_postfix"]
        assert cfg.irc_throttle_limit == data["irc_throttle_limit"]
        assert cfg.irc_message_queue == data["irc_message_queue"]
        assert cfg.irc_rejoin_delay == float(data["irc_rejoin_delay"])
        assert cfg.irc_auto_rejoin == data["irc_auto_rejoin"]
        assert cfg.irc_use_sasl == data["irc_use_sasl"]
        assert cfg.irc_sasl_user == data["irc_sasl_user"]
        assert cfg.irc_sasl_password == data["irc_sasl_password"]
        assert cfg.irc_redact_enabled == data["irc_redact_enabled"]
        assert cfg.irc_relaymsg_clean_nicks == data["irc_relaymsg_clean_nicks"]
        assert cfg.irc_tls_verify == data["irc_tls_verify"]
        assert cfg.irc_puppet_ping_interval == data["irc_puppet_ping_interval"]
        assert cfg.irc_puppet_prejoin_commands == [str(c) for c in data["irc_puppet_prejoin_commands"]]

        # -- IRC nested sub-config --
        assert cfg.irc.puppet_idle_timeout_hours == data["irc_puppet_idle_timeout_hours"]
        assert cfg.irc.auto_rejoin == data["irc_auto_rejoin"]
        assert cfg.irc.redact_enabled == data["irc_redact_enabled"]

        # -- Discord fields (via nested sub-config) --
        assert cfg.discord.webhook_cache_ttl == data["discord_webhook_cache_ttl"]
        assert cfg.discord.max_webhooks_per_channel == data["discord_max_webhooks_per_channel"]
        assert cfg.discord.typing_throttle_seconds == float(data["discord_typing_throttle_seconds"])
        assert cfg.discord.queue_consumer_delay == float(data["discord_queue_consumer_delay"])

        # -- XMPP fields (via backward-compatible flat properties) --
        assert cfg.xmpp_avatar_base_url == data["xmpp_avatar_base_url"].strip()
        assert cfg.xmpp_avatar_public_url == data["xmpp_avatar_public_url"].strip()
        assert cfg.xmpp_auto_rejoin == data["xmpp_auto_rejoin"]

        # -- XMPP nested sub-config --
        assert cfg.xmpp.auto_rejoin == data["xmpp_auto_rejoin"]

    @given(data=_valid_config_dict())
    @settings(max_examples=200)
    def test_config_defaults_for_missing_fields(self, data: dict) -> None:
        """CP16: Missing fields in the config dict produce correct defaults.

        **Validates: Requirement 13.5**
        """
        # Build a minimal config with only mappings.
        minimal = {"mappings": data["mappings"]}
        clean_env = {k: "" for k in _ENV_OVERRIDES}
        with mock.patch.dict(os.environ, clean_env, clear=False):
            cfg = Config(minimal)

        # Top-level defaults
        assert cfg.announce_joins_and_quits is True
        assert cfg.announce_extras is False
        assert cfg.identity_cache_ttl_seconds == 3600
        assert cfg.avatar_cache_ttl_seconds == 86400
        assert cfg.content_filter_regex == []
        assert cfg.paste_service_url is None
        assert cfg.remote_nick_format == "<{nick}> "
        assert cfg.edit_suffix == " (edited)"

        # IRC defaults
        assert cfg.irc.puppet_idle_timeout_hours == 24
        assert cfg.irc.puppet_postfix == ""
        assert cfg.irc.throttle_limit == 10
        assert cfg.irc.message_queue == 30
        assert cfg.irc.rejoin_delay == 5.0
        assert cfg.irc.auto_rejoin is True
        assert cfg.irc.use_sasl is False
        assert cfg.irc.sasl_user == ""
        assert cfg.irc.sasl_password == ""
        assert cfg.irc.redact_enabled is False
        assert cfg.irc.relaymsg_clean_nicks is False
        assert cfg.irc.tls_verify is True
        assert cfg.irc.puppet_ping_interval == 120
        assert cfg.irc.puppet_prejoin_commands == []

        # Discord defaults
        assert cfg.discord.webhook_cache_ttl == 86400
        assert cfg.discord.max_webhooks_per_channel == 15
        assert cfg.discord.typing_throttle_seconds == 3.0
        assert cfg.discord.queue_consumer_delay == 0.25

        # XMPP defaults
        assert cfg.xmpp.avatar_base_url is None
        assert cfg.xmpp.avatar_public_url is None
        assert cfg.xmpp.auto_rejoin is True
