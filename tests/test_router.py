"""Test channel router and mappings."""

import pytest

from bridge.gateway.router import ChannelRouter, ChannelMapping, IrcTarget, XmppTarget


class TestChannelRouter:
    """Test channel router."""

    def test_load_empty_config(self):
        # Arrange
        router = ChannelRouter()
        config = {}

        # Act
        router.load_from_config(config)

        # Assert
        assert len(router.all_mappings()) == 0

    def test_load_config_with_mappings(self):
        # Arrange
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {"server": "irc.libera.chat", "channel": "#test", "port": 6667, "tls": False},
                    "xmpp": {"muc_jid": "test@conference.example.com"},
                }
            ]
        }

        # Act
        router.load_from_config(config)

        # Assert
        mappings = router.all_mappings()
        assert len(mappings) == 1
        assert mappings[0].discord_channel_id == "123"
        assert mappings[0].irc.server == "irc.libera.chat"
        assert mappings[0].irc.channel == "#test"
        assert mappings[0].xmpp.muc_jid == "test@conference.example.com"

    def test_load_config_discord_only(self):
        # Arrange
        router = ChannelRouter()
        config = {
            "mappings": [
                {"discord_channel_id": "123"}
            ]
        }

        # Act
        router.load_from_config(config)

        # Assert
        mappings = router.all_mappings()
        assert len(mappings) == 1
        assert mappings[0].irc is None
        assert mappings[0].xmpp is None

    def test_get_mapping_for_discord(self):
        # Arrange
        router = ChannelRouter()
        config = {
            "mappings": [
                {"discord_channel_id": "123", "irc": {"server": "irc.libera.chat", "channel": "#test"}}
            ]
        }
        router.load_from_config(config)

        # Act
        mapping = router.get_mapping_for_discord("123")

        # Assert
        assert mapping is not None
        assert mapping.discord_channel_id == "123"

    def test_get_mapping_for_discord_not_found(self):
        # Arrange
        router = ChannelRouter()
        config = {"mappings": [{"discord_channel_id": "123"}]}
        router.load_from_config(config)

        # Act
        mapping = router.get_mapping_for_discord("999")

        # Assert
        assert mapping is None

    def test_get_mapping_for_irc(self):
        # Arrange
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {"server": "irc.libera.chat", "channel": "#test", "port": 6667, "tls": False},
                }
            ]
        }
        router.load_from_config(config)

        # Act
        mapping = router.get_mapping_for_irc("irc.libera.chat", "#test")

        # Assert
        assert mapping is not None
        assert mapping.discord_channel_id == "123"

    def test_get_mapping_for_irc_not_found(self):
        # Arrange
        router = ChannelRouter()
        config = {
            "mappings": [
                {"discord_channel_id": "123", "irc": {"server": "irc.libera.chat", "channel": "#test"}}
            ]
        }
        router.load_from_config(config)

        # Act
        mapping = router.get_mapping_for_irc("irc.example.com", "#other")

        # Assert
        assert mapping is None

    def test_get_mapping_for_xmpp(self):
        # Arrange
        router = ChannelRouter()
        config = {
            "mappings": [
                {"discord_channel_id": "123", "xmpp": {"muc_jid": "test@conference.example.com"}}
            ]
        }
        router.load_from_config(config)

        # Act
        mapping = router.get_mapping_for_xmpp("test@conference.example.com")

        # Assert
        assert mapping is not None
        assert mapping.discord_channel_id == "123"

    def test_get_mapping_for_xmpp_not_found(self):
        # Arrange
        router = ChannelRouter()
        config = {
            "mappings": [
                {"discord_channel_id": "123", "xmpp": {"muc_jid": "test@conference.example.com"}}
            ]
        }
        router.load_from_config(config)

        # Act
        mapping = router.get_mapping_for_xmpp("other@conference.example.com")

        # Assert
        assert mapping is None

    def test_multiple_mappings(self):
        # Arrange
        router = ChannelRouter()
        config = {
            "mappings": [
                {"discord_channel_id": "123", "irc": {"server": "irc.libera.chat", "channel": "#test"}},
                {"discord_channel_id": "456", "irc": {"server": "irc.libera.chat", "channel": "#other"}},
            ]
        }
        router.load_from_config(config)

        # Act
        mapping1 = router.get_mapping_for_discord("123")
        mapping2 = router.get_mapping_for_discord("456")

        # Assert
        assert mapping1.irc.channel == "#test"
        assert mapping2.irc.channel == "#other"

    def test_load_config_ignores_invalid_entries(self):
        # Arrange
        router = ChannelRouter()
        config = {
            "mappings": [
                "invalid",
                {"discord_channel_id": ""},  # Empty ID
                {"discord_channel_id": "123"},  # Valid
            ]
        }

        # Act
        router.load_from_config(config)

        # Assert
        assert len(router.all_mappings()) == 1

    def test_load_config_not_a_list(self):
        # Arrange
        router = ChannelRouter()
        config = {"mappings": "not a list"}

        # Act
        router.load_from_config(config)

        # Assert
        assert len(router.all_mappings()) == 0
