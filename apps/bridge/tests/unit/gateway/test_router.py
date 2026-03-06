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
                    "irc": {
                        "server": "irc.libera.chat",
                        "channel": "#test",
                        "port": 6667,
                        "tls": False,
                    },
                    "xmpp": {"muc_jid": "test@conference.example.com"},
                }
            ]
        }
        router.load_from_config(config)
        mappings = router.all_mappings()
        assert len(mappings) == 1
        assert mappings[0].discord_channel_id == "123"
        assert mappings[0].irc is not None
        assert mappings[0].irc.server == "irc.libera.chat"
        assert mappings[0].irc.channel == "#test"
        assert mappings[0].xmpp is not None
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
        router.load_from_config(
            {
                "mappings": [
                    {
                        "discord_channel_id": "123",
                        "irc": {"server": "irc.libera.chat", "channel": "#test"},
                    }
                ]
            }
        )
        irc = router.all_mappings()[0].irc
        assert irc is not None
        assert irc.port == 6667
        assert irc.tls is False

    def test_irc_non_dict_value_treated_as_absent(self):
        router = ChannelRouter()
        router.load_from_config({"mappings": [{"discord_channel_id": "123", "irc": "not-a-dict"}]})
        assert router.all_mappings()[0].irc is None

    def test_xmpp_without_muc_jid_treated_as_absent(self):
        router = ChannelRouter()
        router.load_from_config({"mappings": [{"discord_channel_id": "123", "xmpp": {"other_key": "value"}}]})
        assert router.all_mappings()[0].xmpp is None

    def test_xmpp_non_dict_value_treated_as_absent(self):
        router = ChannelRouter()
        router.load_from_config({"mappings": [{"discord_channel_id": "123", "xmpp": "not-a-dict"}]})
        assert router.all_mappings()[0].xmpp is None

    def test_discord_channel_id_coerced_to_string(self):
        router = ChannelRouter()
        router.load_from_config(
            {
                "mappings": [{"discord_channel_id": 123456}]  # integer
            }
        )
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
        m = router.get_mapping_for_discord("123")
        assert m is not None
        assert m.discord_channel_id == "123"

    def test_get_mapping_for_discord_not_found(self):
        router = ChannelRouter()
        router.load_from_config({"mappings": [{"discord_channel_id": "123"}]})
        assert router.get_mapping_for_discord("999") is None

    def test_get_mapping_for_irc(self):
        router = ChannelRouter()
        router.load_from_config(
            {
                "mappings": [
                    {
                        "discord_channel_id": "123",
                        "irc": {
                            "server": "irc.libera.chat",
                            "channel": "#test",
                            "port": 6697,
                            "tls": True,
                        },
                    }
                ]
            }
        )
        mapping = router.get_mapping_for_irc("irc.libera.chat", "#test")
        assert mapping is not None
        assert mapping.discord_channel_id == "123"

    def test_get_mapping_for_irc_wrong_server(self):
        router = ChannelRouter()
        router.load_from_config(
            {
                "mappings": [
                    {
                        "discord_channel_id": "123",
                        "irc": {"server": "irc.libera.chat", "channel": "#test"},
                    }
                ]
            }
        )
        assert router.get_mapping_for_irc("irc.other.net", "#test") is None

    def test_get_mapping_for_irc_wrong_channel(self):
        router = ChannelRouter()
        router.load_from_config(
            {
                "mappings": [
                    {
                        "discord_channel_id": "123",
                        "irc": {"server": "irc.libera.chat", "channel": "#test"},
                    }
                ]
            }
        )
        assert router.get_mapping_for_irc("irc.libera.chat", "#other") is None

    def test_get_mapping_for_irc_on_mapping_without_irc(self):
        router = ChannelRouter()
        router.load_from_config({"mappings": [{"discord_channel_id": "123"}]})
        assert router.get_mapping_for_irc("irc.libera.chat", "#test") is None

    def test_get_mapping_for_irc_not_found(self):
        router = ChannelRouter()
        router.load_from_config(
            {
                "mappings": [
                    {
                        "discord_channel_id": "123",
                        "irc": {"server": "irc.libera.chat", "channel": "#test"},
                    }
                ]
            }
        )
        assert router.get_mapping_for_irc("irc.example.com", "#other") is None

    def test_get_mapping_for_xmpp(self):
        router = ChannelRouter()
        router.load_from_config(
            {
                "mappings": [
                    {
                        "discord_channel_id": "123",
                        "xmpp": {"muc_jid": "test@conference.example.com"},
                    }
                ]
            }
        )
        mapping = router.get_mapping_for_xmpp("test@conference.example.com")
        assert mapping is not None
        assert mapping.discord_channel_id == "123"

    def test_get_mapping_for_xmpp_not_found(self):
        router = ChannelRouter()
        router.load_from_config(
            {
                "mappings": [
                    {
                        "discord_channel_id": "123",
                        "xmpp": {"muc_jid": "test@conference.example.com"},
                    }
                ]
            }
        )
        assert router.get_mapping_for_xmpp("other@conference.example.com") is None

    def test_get_mapping_for_xmpp_on_mapping_without_xmpp(self):
        router = ChannelRouter()
        router.load_from_config({"mappings": [{"discord_channel_id": "123"}]})
        assert router.get_mapping_for_xmpp("test@conference.example.com") is None

    def test_multiple_mappings(self):
        router = ChannelRouter()
        router.load_from_config(
            {
                "mappings": [
                    {
                        "discord_channel_id": "123",
                        "irc": {"server": "irc.libera.chat", "channel": "#test"},
                    },
                    {
                        "discord_channel_id": "456",
                        "irc": {"server": "irc.libera.chat", "channel": "#other"},
                    },
                ]
            }
        )
        m1 = router.get_mapping_for_discord("123")
        m2 = router.get_mapping_for_discord("456")
        assert m1 is not None and m1.irc is not None
        assert m2 is not None and m2.irc is not None
        assert m1.irc.channel == "#test"
        assert m2.irc.channel == "#other"

    def test_load_config_ignores_invalid_entries(self):
        router = ChannelRouter()
        router.load_from_config(
            {
                "mappings": [
                    "invalid",
                    {"discord_channel_id": ""},  # empty ID skipped
                    {"discord_channel_id": "123"},  # valid
                ]
            }
        )
        assert len(router.all_mappings()) == 1

    def test_load_config_not_a_list(self):
        router = ChannelRouter()
        router.load_from_config({"mappings": "not a list"})
        assert len(router.all_mappings()) == 0


class TestChannelRouterDictIndexes:
    """Tests for O(1) dict-indexed lookups (task 2.2)."""

    def _full_config(self, mappings: list[dict]) -> dict:
        return {"mappings": mappings}

    def _mapping_entry(
        self,
        dc_id: str,
        *,
        irc_server: str | None = None,
        irc_channel: str | None = None,
        muc_jid: str | None = None,
    ) -> dict:
        entry: dict = {"discord_channel_id": dc_id}
        if irc_server and irc_channel:
            entry["irc"] = {"server": irc_server, "channel": irc_channel}
        if muc_jid:
            entry["xmpp"] = {"muc_jid": muc_jid}
        return entry

    # -- O(1) lookups return correct mappings --

    def test_discord_lookup_returns_correct_mapping(self):
        router = ChannelRouter()
        router.load_from_config(
            self._full_config(
                [
                    self._mapping_entry("100", irc_server="s1", irc_channel="#a", muc_jid="a@muc"),
                    self._mapping_entry("200", irc_server="s1", irc_channel="#b", muc_jid="b@muc"),
                ]
            )
        )
        m = router.get_mapping_for_discord("100")
        assert m is not None
        assert m.discord_channel_id == "100"
        assert m.irc is not None and m.irc.channel == "#a"

        m2 = router.get_mapping_for_discord("200")
        assert m2 is not None
        assert m2.discord_channel_id == "200"
        assert m2.irc is not None and m2.irc.channel == "#b"

    def test_irc_lookup_returns_correct_mapping(self):
        router = ChannelRouter()
        router.load_from_config(
            self._full_config(
                [
                    self._mapping_entry("100", irc_server="irc.example.com", irc_channel="#general"),
                    self._mapping_entry("200", irc_server="irc.example.com", irc_channel="#random"),
                ]
            )
        )
        m = router.get_mapping_for_irc("irc.example.com", "#general")
        assert m is not None
        assert m.discord_channel_id == "100"

        m2 = router.get_mapping_for_irc("irc.example.com", "#random")
        assert m2 is not None
        assert m2.discord_channel_id == "200"

    def test_xmpp_lookup_returns_correct_mapping(self):
        router = ChannelRouter()
        router.load_from_config(
            self._full_config(
                [
                    self._mapping_entry("100", muc_jid="room1@conference.example.com"),
                    self._mapping_entry("200", muc_jid="room2@conference.example.com"),
                ]
            )
        )
        m = router.get_mapping_for_xmpp("room1@conference.example.com")
        assert m is not None
        assert m.discord_channel_id == "100"

        m2 = router.get_mapping_for_xmpp("room2@conference.example.com")
        assert m2 is not None
        assert m2.discord_channel_id == "200"

    # -- Duplicate key warning and last-write-wins --

    def test_duplicate_discord_id_last_write_wins(self):
        router = ChannelRouter()
        router.load_from_config(
            self._full_config(
                [
                    self._mapping_entry("100", irc_server="s1", irc_channel="#first"),
                    self._mapping_entry("100", irc_server="s1", irc_channel="#second"),
                ]
            )
        )
        m = router.get_mapping_for_discord("100")
        assert m is not None
        assert m.irc is not None
        assert m.irc.channel == "#second", "last-write-wins: second mapping should win"

    def test_duplicate_irc_key_last_write_wins(self):
        router = ChannelRouter()
        router.load_from_config(
            self._full_config(
                [
                    self._mapping_entry("100", irc_server="irc.example.com", irc_channel="#dup"),
                    self._mapping_entry("200", irc_server="irc.example.com", irc_channel="#dup"),
                ]
            )
        )
        m = router.get_mapping_for_irc("irc.example.com", "#dup")
        assert m is not None
        assert m.discord_channel_id == "200", "last-write-wins: second mapping should win"

    def test_duplicate_xmpp_key_last_write_wins(self):
        router = ChannelRouter()
        router.load_from_config(
            self._full_config(
                [
                    self._mapping_entry("100", muc_jid="room@conference.example.com"),
                    self._mapping_entry("200", muc_jid="room@conference.example.com"),
                ]
            )
        )
        m = router.get_mapping_for_xmpp("room@conference.example.com")
        assert m is not None
        assert m.discord_channel_id == "200", "last-write-wins: second mapping should win"

    def test_duplicate_discord_id_logs_warning(self, capfd):
        """Duplicate discord_channel_id triggers a loguru warning."""
        import io

        from loguru import logger

        sink = io.StringIO()
        handler_id = logger.add(sink, format="{message}", level="WARNING")
        try:
            router = ChannelRouter()
            router.load_from_config(
                self._full_config(
                    [
                        self._mapping_entry("100"),
                        self._mapping_entry("100"),
                    ]
                )
            )
        finally:
            logger.remove(handler_id)

        assert "Duplicate discord_channel_id" in sink.getvalue()

    def test_duplicate_irc_key_logs_warning(self):
        import io

        from loguru import logger

        sink = io.StringIO()
        handler_id = logger.add(sink, format="{message}", level="WARNING")
        try:
            router = ChannelRouter()
            router.load_from_config(
                self._full_config(
                    [
                        self._mapping_entry("100", irc_server="s", irc_channel="#c"),
                        self._mapping_entry("200", irc_server="s", irc_channel="#c"),
                    ]
                )
            )
        finally:
            logger.remove(handler_id)

        assert "Duplicate IRC key" in sink.getvalue()

    def test_duplicate_xmpp_key_logs_warning(self):
        import io

        from loguru import logger

        sink = io.StringIO()
        handler_id = logger.add(sink, format="{message}", level="WARNING")
        try:
            router = ChannelRouter()
            router.load_from_config(
                self._full_config(
                    [
                        self._mapping_entry("100", muc_jid="r@muc"),
                        self._mapping_entry("200", muc_jid="r@muc"),
                    ]
                )
            )
        finally:
            logger.remove(handler_id)

        assert "Duplicate XMPP MUC JID" in sink.getvalue()

    # -- Missing key returns None --

    def test_missing_discord_key_returns_none(self):
        router = ChannelRouter()
        router.load_from_config(self._full_config([self._mapping_entry("100")]))
        assert router.get_mapping_for_discord("nonexistent") is None

    def test_missing_irc_key_returns_none(self):
        router = ChannelRouter()
        router.load_from_config(self._full_config([self._mapping_entry("100", irc_server="s", irc_channel="#c")]))
        assert router.get_mapping_for_irc("s", "#other") is None

    def test_missing_xmpp_key_returns_none(self):
        router = ChannelRouter()
        router.load_from_config(self._full_config([self._mapping_entry("100", muc_jid="r@muc")]))
        assert router.get_mapping_for_xmpp("other@muc") is None

    # -- Empty config produces empty indexes --

    def test_empty_config_produces_empty_indexes(self):
        router = ChannelRouter()
        router.load_from_config({})
        assert router._by_discord == {}
        assert router._by_irc == {}
        assert router._by_xmpp == {}

    def test_empty_mappings_list_produces_empty_indexes(self):
        router = ChannelRouter()
        router.load_from_config({"mappings": []})
        assert router._by_discord == {}
        assert router._by_irc == {}
        assert router._by_xmpp == {}

    def test_non_list_mappings_produces_empty_indexes(self):
        router = ChannelRouter()
        router.load_from_config({"mappings": "not a list"})
        assert router._by_discord == {}
        assert router._by_irc == {}
        assert router._by_xmpp == {}


# ---------------------------------------------------------------------------
# Property-based tests (hypothesis)
# ---------------------------------------------------------------------------

from bridge.gateway.router import ChannelMapping
from hypothesis import given, settings
from hypothesis import strategies as st

# -- Strategies --

_discord_ids = st.text(alphabet=st.sampled_from("0123456789"), min_size=1, max_size=6)
_irc_servers = st.sampled_from(["irc.libera.chat", "irc.example.com", "irc.freenode.net"])
_irc_channels = st.sampled_from(["#general", "#random", "#test", "#dev", "#help"])
_muc_jids = st.sampled_from(
    [
        "room1@conference.example.com",
        "room2@conference.example.com",
        "room3@conference.example.com",
        "lobby@muc.example.org",
        "chat@muc.example.org",
    ]
)

_mapping_entry_st = st.fixed_dictionaries(
    {"discord_channel_id": _discord_ids},
    optional={
        "irc": st.fixed_dictionaries({"server": _irc_servers, "channel": _irc_channels}),
        "xmpp": st.fixed_dictionaries({"muc_jid": _muc_jids}),
    },
)


def _linear_scan_discord(mappings: list[ChannelMapping], discord_id: str) -> ChannelMapping | None:
    """Reference linear scan — returns LAST match (last-write-wins)."""
    result = None
    for m in mappings:
        if m.discord_channel_id == discord_id:
            result = m
    return result


def _linear_scan_irc(mappings: list[ChannelMapping], server: str, channel: str) -> ChannelMapping | None:
    result = None
    for m in mappings:
        if m.irc and m.irc.server == server and m.irc.channel == channel:
            result = m
    return result


def _linear_scan_xmpp(mappings: list[ChannelMapping], muc_jid: str) -> ChannelMapping | None:
    result = None
    for m in mappings:
        if m.xmpp and m.xmpp.muc_jid == muc_jid:
            result = m
    return result


class TestRouterLookupEquivalenceProperty:
    """Property 1: Router lookup equivalence.

    **Validates: Requirements 2.2, 2.3, 2.4**

    For any list of valid channel mappings and any query, dict-indexed lookup
    returns the same ChannelMapping (or None) as a linear scan with
    last-write-wins semantics.
    """

    @given(
        entries=st.lists(_mapping_entry_st, min_size=0, max_size=20),
        query_discord_id=_discord_ids,
    )
    @settings(max_examples=200)
    def test_discord_lookup_matches_linear_scan(self, entries: list[dict], query_discord_id: str):
        """**Validates: Requirements 2.2**"""
        router = ChannelRouter()
        router.load_from_config({"mappings": entries})

        dict_result = router.get_mapping_for_discord(query_discord_id)
        linear_result = _linear_scan_discord(router._mappings, query_discord_id)

        assert dict_result is linear_result

    @given(
        entries=st.lists(_mapping_entry_st, min_size=0, max_size=20),
        query_server=_irc_servers,
        query_channel=_irc_channels,
    )
    @settings(max_examples=200)
    def test_irc_lookup_matches_linear_scan(
        self,
        entries: list[dict],
        query_server: str,
        query_channel: str,
    ):
        """**Validates: Requirements 2.3**"""
        router = ChannelRouter()
        router.load_from_config({"mappings": entries})

        dict_result = router.get_mapping_for_irc(query_server, query_channel)
        linear_result = _linear_scan_irc(router._mappings, query_server, query_channel)

        assert dict_result is linear_result

    @given(
        entries=st.lists(_mapping_entry_st, min_size=0, max_size=20),
        query_muc_jid=_muc_jids,
    )
    @settings(max_examples=200)
    def test_xmpp_lookup_matches_linear_scan(self, entries: list[dict], query_muc_jid: str):
        """**Validates: Requirements 2.4**"""
        router = ChannelRouter()
        router.load_from_config({"mappings": entries})

        dict_result = router.get_mapping_for_xmpp(query_muc_jid)
        linear_result = _linear_scan_xmpp(router._mappings, query_muc_jid)

        assert dict_result is linear_result
