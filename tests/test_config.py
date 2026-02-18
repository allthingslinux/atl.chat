"""Tests for config loading."""

from __future__ import annotations

import tempfile

from bridge.config import Config, load_config


def test_load_config_missing_file() -> None:
    """Missing file returns empty dict."""
    data = load_config("/nonexistent/path.yaml")
    assert data == {}


def test_load_config_valid_yaml() -> None:
    """Valid YAML loads correctly."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        f.write(b"mappings:\n  - discord_channel_id: '123'\n    irc:\n      server: irc.test\n")
        f.flush()
        data = load_config(f.name)

    assert "mappings" in data
    assert len(data["mappings"]) == 1
    assert data["mappings"][0]["discord_channel_id"] == "123"
    assert data["mappings"][0]["irc"]["server"] == "irc.test"


def test_config_properties() -> None:
    """Config properties return correct defaults and values."""
    cfg = Config(
        {
            "announce_joins_and_quits": False,
            "announce_extras": True,
            "identity_cache_ttl_seconds": 1800,
            "irc_puppet_idle_timeout_hours": 12,
            "irc_puppet_postfix": "|d",
        }
    )

    assert cfg.announce_joins_and_quits is False
    assert cfg.announce_extras is True
    assert cfg.identity_cache_ttl_seconds == 1800
    assert cfg.avatar_cache_ttl_seconds == 86400  # default
    assert cfg.irc_puppet_idle_timeout_hours == 12
    assert cfg.irc_puppet_postfix == "|d"


def test_config_mappings_empty() -> None:
    """Empty or missing mappings returns []."""
    assert Config({}).mappings == []
    assert Config({"mappings": []}).mappings == []
    assert Config({"mappings": "not a list"}).mappings == []
