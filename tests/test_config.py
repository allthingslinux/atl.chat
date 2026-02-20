"""Test config loading and parsing."""

import tempfile
from pathlib import Path

import pytest

from bridge.config import Config, _deep_update, load_config


class TestDeepUpdate:
    """Test deep dictionary merge."""

    def test_deep_update_simple(self):
        # Arrange
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}

        # Act
        result = _deep_update(base, override)

        # Assert
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_update_nested(self):
        # Arrange
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99, "z": 100}}

        # Act
        result = _deep_update(base, override)

        # Assert
        assert result == {"a": {"x": 1, "y": 99, "z": 100}, "b": 3}

    def test_deep_update_preserves_base(self):
        # Arrange
        base = {"a": 1}
        override = {"b": 2}

        # Act
        _deep_update(base, override)

        # Assert
        assert base == {"a": 1}  # Original unchanged


class TestLoadConfig:
    """Test config file loading."""

    def test_load_config_from_yaml(self):
        # Arrange
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("test_key: test_value\n")
            f.write("mappings:\n")
            f.write("  - discord_channel_id: '123'\n")
            path = f.name

        try:
            # Act
            config = load_config(path)

            # Assert
            assert config["test_key"] == "test_value"
            assert len(config["mappings"]) == 1
        finally:
            Path(path).unlink()

    def test_load_config_missing_file(self):
        # Arrange
        path = "/nonexistent/config.yaml"

        # Act
        config = load_config(path)

        # Assert
        assert config == {}

    def test_load_config_empty_file(self):
        # Arrange
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            path = f.name

        try:
            # Act
            config = load_config(path)

            # Assert
            assert config == {}
        finally:
            Path(path).unlink()

    def test_load_config_invalid_yaml(self):
        # Arrange
        import yaml
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("not: a: valid: yaml:")
            path = f.name

        try:
            # Act & Assert
            with pytest.raises((ValueError, KeyError, TypeError, yaml.scanner.ScannerError)):
                load_config(path)
        finally:
            Path(path).unlink()


class TestConfig:
    """Test Config accessor class."""

    def test_config_get_simple(self):
        # Arrange
        config = Config({"key": "value"})

        # Act
        result = config.get("key")

        # Assert
        assert result == "value"

    def test_config_get_nested(self):
        # Arrange
        config = Config({"a": {"b": {"c": "value"}}})

        # Act
        result = config.get("a.b.c")

        # Assert
        assert result == "value"

    def test_config_get_default(self):
        # Arrange
        config = Config({})

        # Act
        result = config.get("missing", "default")

        # Assert
        assert result == "default"

    def test_config_get_missing_no_default(self):
        # Arrange
        config = Config({})

        # Act
        result = config.get("missing")

        # Assert
        assert result is None

    def test_config_getitem(self):
        # Arrange
        config = Config({"key": "value"})

        # Act
        result = config["key"]

        # Assert
        assert result == "value"

    def test_config_contains(self):
        # Arrange
        config = Config({"key": "value"})

        # Act & Assert
        assert "key" in config
        assert "missing" not in config

    def test_config_mappings_property(self):
        # Arrange
        mappings = [{"discord_channel_id": "123"}]
        config = Config({"mappings": mappings})

        # Act
        result = config.mappings

        # Assert
        assert result == mappings

    def test_config_mappings_empty(self):
        # Arrange
        config = Config({})

        # Act
        result = config.mappings

        # Assert
        assert result == []

    def test_config_announce_joins_and_quits_default(self):
        # Arrange
        config = Config({})

        # Act
        result = config.announce_joins_and_quits

        # Assert
        assert result is True

    def test_config_announce_joins_and_quits_false(self):
        # Arrange
        config = Config({"announce_joins_and_quits": False})

        # Act
        result = config.announce_joins_and_quits

        # Assert
        assert result is False

    def test_config_irc_puppet_idle_timeout_default(self):
        # Arrange
        config = Config({})

        # Act
        result = config.irc_puppet_idle_timeout_hours

        # Assert
        assert result == 24

    def test_config_irc_puppet_idle_timeout_custom(self):
        # Arrange
        config = Config({"irc_puppet_idle_timeout_hours": 48})

        # Act
        result = config.irc_puppet_idle_timeout_hours

        # Assert
        assert result == 48

    def test_config_reload(self):
        # Arrange
        config = Config({"old": "value"})

        # Act
        config.reload({"new": "value"})

        # Assert
        assert config.get("new") == "value"
        assert config.get("old") is None

    def test_config_raw_property(self):
        data = {"key": "value"}
        config = Config(data)
        assert config.raw == data

    def test_config_none_defaults_to_empty(self):
        config = Config(None)
        assert config.raw == {}

    def test_config_announce_extras_default(self):
        assert Config({}).announce_extras is False

    def test_config_announce_extras_true(self):
        assert Config({"announce_extras": True}).announce_extras is True

    def test_config_identity_cache_ttl_default(self):
        assert Config({}).identity_cache_ttl_seconds == 3600

    def test_config_identity_cache_ttl_custom(self):
        assert Config({"identity_cache_ttl_seconds": 600}).identity_cache_ttl_seconds == 600

    def test_config_avatar_cache_ttl_default(self):
        assert Config({}).avatar_cache_ttl_seconds == 86400

    def test_config_irc_puppet_postfix_default(self):
        assert Config({}).irc_puppet_postfix == ""

    def test_config_irc_puppet_postfix_custom(self):
        assert Config({"irc_puppet_postfix": "|d"}).irc_puppet_postfix == "|d"

    def test_config_irc_throttle_limit_default(self):
        assert Config({}).irc_throttle_limit == 10

    def test_config_irc_message_queue_default(self):
        assert Config({}).irc_message_queue == 30

    def test_config_irc_rejoin_delay_default(self):
        assert Config({}).irc_rejoin_delay == 5.0

    def test_config_irc_auto_rejoin_default(self):
        assert Config({}).irc_auto_rejoin is True

    def test_config_irc_auto_rejoin_false(self):
        assert Config({"irc_auto_rejoin": False}).irc_auto_rejoin is False

    def test_config_irc_use_sasl_default(self):
        assert Config({}).irc_use_sasl is False

    def test_config_irc_sasl_user_default(self):
        assert Config({}).irc_sasl_user == ""

    def test_config_irc_sasl_password_default(self):
        assert Config({}).irc_sasl_password == ""

    def test_config_content_filter_regex_default(self):
        assert Config({}).content_filter_regex == []

    def test_config_content_filter_regex_list(self):
        assert Config({"content_filter_regex": ["spam", "ads"]}).content_filter_regex == ["spam", "ads"]

    def test_config_content_filter_regex_non_list(self):
        assert Config({"content_filter_regex": "not-a-list"}).content_filter_regex == []

    def test_deep_update_non_dict_replaces_dict(self):
        result = _deep_update({"a": {"x": 1}}, {"a": "scalar"})
        assert result == {"a": "scalar"}
