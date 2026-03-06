"""Test config loading and parsing."""

import tempfile
from pathlib import Path

import pytest
from bridge.config import Config, _deep_update, load_config, validate_config
from bridge.errors import BridgeConfigurationError


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
            with pytest.raises((ValueError, KeyError, TypeError, yaml.YAMLError)):
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
        assert Config({}).announce_joins_and_quits is True

    def test_config_announce_joins_and_quits_false(self):
        assert Config({"announce_joins_and_quits": False}).announce_joins_and_quits is False

    def test_config_irc_puppet_idle_timeout_default(self):
        assert Config({}).irc_puppet_idle_timeout_hours == 24

    def test_config_irc_puppet_idle_timeout_custom(self):
        assert Config({"irc_puppet_idle_timeout_hours": 48}).irc_puppet_idle_timeout_hours == 48

    def test_config_reload(self):
        config = Config({"old": "value"})
        config.reload({"new": "value"})
        assert config.get("new") == "value"
        assert config.get("old") is None

    def test_config_raw_property(self):
        data = {"key": "value"}
        assert Config(data).raw == data

    def test_config_none_defaults_to_empty(self):
        assert Config(None).raw == {}

    def test_config_announce_extras_true(self):
        assert Config({"announce_extras": True}).announce_extras is True

    def test_config_identity_cache_ttl_custom(self):
        assert Config({"identity_cache_ttl_seconds": 600}).identity_cache_ttl_seconds == 600

    def test_config_irc_puppet_postfix_custom(self):
        assert Config({"irc_puppet_postfix": "|d"}).irc_puppet_postfix == "|d"

    def test_config_irc_auto_rejoin_false(self):
        assert Config({"irc_auto_rejoin": False}).irc_auto_rejoin is False

    def test_config_content_filter_regex_list(self):
        assert Config({"content_filter_regex": ["spam", "ads"]}).content_filter_regex == [
            "spam",
            "ads",
        ]

    def test_config_content_filter_regex_non_list(self):
        assert Config({"content_filter_regex": "not-a-list"}).content_filter_regex == []

    def test_config_irc_puppet_ping_interval_default(self):
        assert Config({}).irc_puppet_ping_interval == 120

    def test_config_irc_puppet_ping_interval_custom(self):
        assert Config({"irc_puppet_ping_interval": 60}).irc_puppet_ping_interval == 60

    def test_config_irc_puppet_prejoin_commands_default(self):
        assert Config({}).irc_puppet_prejoin_commands == []

    def test_config_irc_puppet_prejoin_commands_list(self):
        cmds = ["MODE {nick} +D", "PRIVMSG NickServ IDENTIFY pass"]
        assert Config({"irc_puppet_prejoin_commands": cmds}).irc_puppet_prejoin_commands == cmds

    def test_config_irc_puppet_prejoin_commands_non_list(self):
        assert Config({"irc_puppet_prejoin_commands": "not-a-list"}).irc_puppet_prejoin_commands == []

    @pytest.mark.parametrize(
        "prop,expected",
        [
            ("announce_extras", False),
            ("identity_cache_ttl_seconds", 3600),
            ("avatar_cache_ttl_seconds", 86400),
            ("irc_puppet_postfix", ""),
            ("irc_throttle_limit", 10),
            ("irc_message_queue", 30),
            ("irc_rejoin_delay", 5.0),
            ("irc_auto_rejoin", True),
            ("irc_use_sasl", False),
            ("irc_sasl_user", ""),
            ("irc_sasl_password", ""),
            ("content_filter_regex", []),
        ],
    )
    def test_config_property_defaults(self, prop, expected):
        assert getattr(Config({}), prop) == expected

    def test_deep_update_non_dict_replaces_dict(self):
        result = _deep_update({"a": {"x": 1}}, {"a": "scalar"})
        assert result == {"a": "scalar"}

    def test_reload_validates_mappings_structure(self):
        """Invalid mappings raise BridgeConfigurationError."""
        config = Config({})
        with pytest.raises(BridgeConfigurationError) as exc_info:
            config.reload({"mappings": [{}]})
        assert exc_info.value.code == "missing_discord_channel_id"

    def test_reload_validates_mappings_item_type(self):
        config = Config({})
        with pytest.raises(BridgeConfigurationError) as exc_info:
            config.reload({"mappings": ["not-a-dict"]})
        assert exc_info.value.code == "invalid_mapping_item"

    def test_reload_skips_validation_when_validate_false(self):
        """reload(..., validate=False) allows invalid structure."""
        config = Config({})
        config.reload({"mappings": [{}]}, validate=False)
        assert config.mappings == [{}]


class TestValidateConfig:
    """Test validate_config field-type validation and defaults."""

    def test_minimal_config_with_mappings(self):
        """A minimal config with just mappings should work."""
        data = {"mappings": [{"discord_channel_id": "123"}]}
        cfg = validate_config(data)
        assert cfg.mappings == [{"discord_channel_id": "123"}]
        # Defaults should be populated via Config
        assert cfg.announce_joins_and_quits is True
        assert cfg.edit_suffix == " (edited)"
        assert cfg.remote_nick_format == "<{nick}> "

    def test_empty_config_is_valid(self):
        """Empty dict is valid (mappings defaults to [])."""
        cfg = validate_config({})
        assert cfg.mappings == []

    def test_non_dict_raises(self):
        with pytest.raises(BridgeConfigurationError) as exc_info:
            validate_config("not a dict")  # type: ignore[arg-type]
        assert exc_info.value.code == "invalid_config_type"

    def test_mappings_wrong_type_raises(self):
        with pytest.raises(BridgeConfigurationError) as exc_info:
            validate_config({"mappings": "not-a-list"})
        assert exc_info.value.code == "invalid_field_types"
        assert "mappings" in str(exc_info.value)

    def test_bool_field_wrong_type_raises(self):
        with pytest.raises(BridgeConfigurationError) as exc_info:
            validate_config({"announce_joins_and_quits": "yes"})
        assert exc_info.value.code == "invalid_field_types"

    def test_int_field_wrong_type_raises(self):
        with pytest.raises(BridgeConfigurationError) as exc_info:
            validate_config({"identity_cache_ttl_seconds": "not-int"})
        assert exc_info.value.code == "invalid_field_types"

    def test_float_field_accepts_int(self):
        """Float fields should accept int values (e.g. rejoin_delay: 5)."""
        cfg = validate_config({"irc_rejoin_delay": 5})
        assert cfg.irc.rejoin_delay == 5.0

    def test_none_value_accepted_for_optional_fields(self):
        """None is acceptable for optional str|None fields."""
        cfg = validate_config({"paste_service_url": None})
        assert cfg.paste_service_url is None

    def test_validates_and_returns_config_instance(self):
        data = {
            "mappings": [{"discord_channel_id": "456"}],
            "irc_puppet_idle_timeout_hours": 48,
            "announce_extras": True,
        }
        cfg = validate_config(data)
        assert cfg.irc.puppet_idle_timeout_hours == 48
        assert cfg.announce_extras is True

    def test_validates_mappings_structure(self):
        """validate_config also runs Config._validate for mappings structure."""
        with pytest.raises(BridgeConfigurationError) as exc_info:
            validate_config({"mappings": [{}]})
        assert exc_info.value.code == "missing_discord_channel_id"

    def test_list_field_wrong_type_raises(self):
        with pytest.raises(BridgeConfigurationError) as exc_info:
            validate_config({"content_filter_regex": 42})
        assert exc_info.value.code == "invalid_field_types"

    def test_int_provided_for_bool_field_accepted(self):
        """YAML may parse True/False as 1/0 — int for bool is coerced."""
        cfg = validate_config({"irc_auto_rejoin": 0})
        # The Config class coerces via bool()
        assert cfg.irc.auto_rejoin is False
