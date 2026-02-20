"""Test channel router and mappings."""


from bridge.gateway.router import ChannelRouter


class TestChannelRouter:
    """Test channel router."""

    def test_load_empty_config(self):
        router = ChannelRouter()
        router.load_from_config({})
        assert len(router.all_mappings()) == 0

    def test_load_config_with_mappings(self):
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
        router.load_from_config(config)
        mappings = router.all_mappings()
        assert len(mappings) == 1
        assert mappings[0].discord_channel_id == "123"
        assert mappings[0].irc.server == "irc.libera.chat"
        assert mappings[0].irc.channel == "#test"
        assert mappings[0].xmpp.muc_jid == "test@conference.example.com"

    def test_load_config_discord_only(self):
        router = ChannelRouter()
        router.load_from_config({"mappings": [{"discord_channel_id": "123"}]})
        mappings = router.all_mappings()
        assert len(mappings) == 1
        assert mappings[0].irc is None
        assert mappings[0].xmpp is None

    def test_irc_defaults_port_and_tls(self):
        router = ChannelRouter()
        router.load_from_config({
            "mappings": [{"discord_channel_id": "123",
                          "irc": {"server": "irc.libera.chat", "channel": "#test"}}]
        })
        irc = router.all_mappings()[0].irc
        assert irc.port == 6667
        assert irc.tls is False

    def test_irc_non_dict_value_treated_as_absent(self):
        router = ChannelRouter()
        router.load_from_config({
            "mappings": [{"discord_channel_id": "123", "irc": "not-a-dict"}]
        })
        assert router.all_mappings()[0].irc is None

    def test_xmpp_without_muc_jid_treated_as_absent(self):
        router = ChannelRouter()
        router.load_from_config({
            "mappings": [{"discord_channel_id": "123", "xmpp": {"other_key": "value"}}]
        })
        assert router.all_mappings()[0].xmpp is None

    def test_xmpp_non_dict_value_treated_as_absent(self):
        router = ChannelRouter()
        router.load_from_config({
            "mappings": [{"discord_channel_id": "123", "xmpp": "not-a-dict"}]
        })
        assert router.all_mappings()[0].xmpp is None

    def test_discord_channel_id_coerced_to_string(self):
        router = ChannelRouter()
        router.load_from_config({
            "mappings": [{"discord_channel_id": 123456}]  # integer
        })
        assert router.all_mappings()[0].discord_channel_id == "123456"

    def test_load_config_called_twice_replaces_mappings(self):
        router = ChannelRouter()
        router.load_from_config({"mappings": [{"discord_channel_id": "111"}]})
        router.load_from_config({"mappings": [{"discord_channel_id": "222"}]})
        mappings = router.all_mappings()
        assert len(mappings) == 1
        assert mappings[0].discord_channel_id == "222"

    def test_all_mappings_returns_copy(self):
        router = ChannelRouter()
        router.load_from_config({"mappings": [{"discord_channel_id": "123"}]})
        copy = router.all_mappings()
        copy.clear()
        assert len(router.all_mappings()) == 1

    def test_get_mapping_for_discord(self):
        router = ChannelRouter()
        router.load_from_config({"mappings": [{"discord_channel_id": "123"}]})
        assert router.get_mapping_for_discord("123") is not None
        assert router.get_mapping_for_discord("123").discord_channel_id == "123"

    def test_get_mapping_for_discord_not_found(self):
        router = ChannelRouter()
        router.load_from_config({"mappings": [{"discord_channel_id": "123"}]})
        assert router.get_mapping_for_discord("999") is None

    def test_get_mapping_for_irc(self):
        router = ChannelRouter()
        router.load_from_config({
            "mappings": [{
                "discord_channel_id": "123",
                "irc": {"server": "irc.libera.chat", "channel": "#test", "port": 6697, "tls": True},
            }]
        })
        mapping = router.get_mapping_for_irc("irc.libera.chat", "#test")
        assert mapping is not None
        assert mapping.discord_channel_id == "123"

    def test_get_mapping_for_irc_wrong_server(self):
        router = ChannelRouter()
        router.load_from_config({
            "mappings": [{
                "discord_channel_id": "123",
                "irc": {"server": "irc.libera.chat", "channel": "#test"},
            }]
        })
        assert router.get_mapping_for_irc("irc.other.net", "#test") is None

    def test_get_mapping_for_irc_wrong_channel(self):
        router = ChannelRouter()
        router.load_from_config({
            "mappings": [{
                "discord_channel_id": "123",
                "irc": {"server": "irc.libera.chat", "channel": "#test"},
            }]
        })
        assert router.get_mapping_for_irc("irc.libera.chat", "#other") is None

    def test_get_mapping_for_irc_on_mapping_without_irc(self):
        router = ChannelRouter()
        router.load_from_config({"mappings": [{"discord_channel_id": "123"}]})
        assert router.get_mapping_for_irc("irc.libera.chat", "#test") is None

    def test_get_mapping_for_irc_not_found(self):
        router = ChannelRouter()
        router.load_from_config({
            "mappings": [{"discord_channel_id": "123",
                          "irc": {"server": "irc.libera.chat", "channel": "#test"}}]
        })
        assert router.get_mapping_for_irc("irc.example.com", "#other") is None

    def test_get_mapping_for_xmpp(self):
        router = ChannelRouter()
        router.load_from_config({
            "mappings": [{"discord_channel_id": "123",
                          "xmpp": {"muc_jid": "test@conference.example.com"}}]
        })
        mapping = router.get_mapping_for_xmpp("test@conference.example.com")
        assert mapping is not None
        assert mapping.discord_channel_id == "123"

    def test_get_mapping_for_xmpp_not_found(self):
        router = ChannelRouter()
        router.load_from_config({
            "mappings": [{"discord_channel_id": "123",
                          "xmpp": {"muc_jid": "test@conference.example.com"}}]
        })
        assert router.get_mapping_for_xmpp("other@conference.example.com") is None

    def test_get_mapping_for_xmpp_on_mapping_without_xmpp(self):
        router = ChannelRouter()
        router.load_from_config({"mappings": [{"discord_channel_id": "123"}]})
        assert router.get_mapping_for_xmpp("test@conference.example.com") is None

    def test_multiple_mappings(self):
        router = ChannelRouter()
        router.load_from_config({
            "mappings": [
                {"discord_channel_id": "123",
                 "irc": {"server": "irc.libera.chat", "channel": "#test"}},
                {"discord_channel_id": "456",
                 "irc": {"server": "irc.libera.chat", "channel": "#other"}},
            ]
        })
        assert router.get_mapping_for_discord("123").irc.channel == "#test"
        assert router.get_mapping_for_discord("456").irc.channel == "#other"

    def test_load_config_ignores_invalid_entries(self):
        router = ChannelRouter()
        router.load_from_config({
            "mappings": [
                "invalid",
                {"discord_channel_id": ""},   # empty ID skipped
                {"discord_channel_id": "123"},  # valid
            ]
        })
        assert len(router.all_mappings()) == 1

    def test_load_config_not_a_list(self):
        router = ChannelRouter()
        router.load_from_config({"mappings": "not a list"})
        assert len(router.all_mappings()) == 0
