"""Property-based tests for channel router bijectivity (CP7).

**Validates: Requirement 4.1**

Property CP7: Channel Router Bijectivity
  For any mapping in the router, looking up by Discord channel ID,
  IRC server+channel, or XMPP MUC JID returns the same ChannelMapping object.
  Router lookups must be consistent across all protocol directions.
"""

from __future__ import annotations

from bridge.gateway.router import ChannelRouter
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Unique identifiers for each protocol key space.
_discord_id = st.from_regex(r"[0-9]{6,20}", fullmatch=True)
_irc_server = st.from_regex(r"[a-z]{3,10}\.irc\.net", fullmatch=True)
_irc_channel = st.from_regex(r"#[a-z]{2,12}", fullmatch=True)
_xmpp_muc = st.from_regex(r"[a-z]{3,12}@conference\.[a-z]{3,8}\.org", fullmatch=True)


@st.composite
def _mapping_dicts(draw: st.DrawFn) -> list[dict]:
    """Generate a list of mapping dicts with unique keys across all entries.

    Each mapping has a unique discord_channel_id, a unique IRC
    server+channel pair, and a unique XMPP MUC JID.
    """
    n = draw(st.integers(min_value=1, max_value=8))

    discord_ids = draw(st.lists(_discord_id, min_size=n, max_size=n, unique=True))
    irc_servers = draw(st.lists(_irc_server, min_size=n, max_size=n))
    irc_channels = draw(st.lists(_irc_channel, min_size=n, max_size=n))
    xmpp_jids = draw(st.lists(_xmpp_muc, min_size=n, max_size=n, unique=True))

    # Ensure IRC (server, channel) pairs are unique.
    irc_pairs: set[tuple[str, str]] = set()
    mappings: list[dict] = []
    for i in range(n):
        pair = (irc_servers[i], irc_channels[i])
        if pair in irc_pairs:
            # Skip duplicate IRC pair to keep uniqueness.
            continue
        irc_pairs.add(pair)
        mappings.append(
            {
                "discord_channel_id": discord_ids[i],
                "irc": {
                    "server": irc_servers[i],
                    "port": 6667,
                    "tls": False,
                    "channel": irc_channels[i],
                },
                "xmpp": {"muc_jid": xmpp_jids[i]},
            }
        )
    return mappings


# ---------------------------------------------------------------------------
# CP7: Channel Router Bijectivity
# ---------------------------------------------------------------------------


class TestChannelRouterBijectivity:
    """All three lookup methods return the same ChannelMapping object.

    **Validates: Requirement 4.1**
    """

    @given(mapping_dicts=_mapping_dicts())
    @settings(max_examples=200)
    def test_lookups_return_same_object(
        self,
        mapping_dicts: list[dict],
    ) -> None:
        """For every mapping loaded, Discord/IRC/XMPP lookups return the
        identical ChannelMapping instance.

        **Validates: Requirement 4.1**
        """
        router = ChannelRouter()
        router.load_from_config({"mappings": mapping_dicts})

        for entry in mapping_dicts:
            discord_id = entry["discord_channel_id"]
            irc_cfg = entry["irc"]
            xmpp_cfg = entry["xmpp"]

            by_discord = router.get_mapping_for_discord(discord_id)
            by_irc = router.get_mapping_for_irc(irc_cfg["server"], irc_cfg["channel"])
            by_xmpp = router.get_mapping_for_xmpp(xmpp_cfg["muc_jid"])

            assert by_discord is not None, f"Discord lookup failed for {discord_id}"
            assert by_irc is not None, f"IRC lookup failed for ({irc_cfg['server']}, {irc_cfg['channel']})"
            assert by_xmpp is not None, f"XMPP lookup failed for {xmpp_cfg['muc_jid']}"

            # All three lookups must return the exact same object (identity).
            assert by_discord is by_irc, f"Discord and IRC lookups returned different objects for discord={discord_id}"
            assert by_discord is by_xmpp, (
                f"Discord and XMPP lookups returned different objects for discord={discord_id}"
            )

    @given(mapping_dicts=_mapping_dicts())
    @settings(max_examples=200)
    def test_mapping_fields_match_config(
        self,
        mapping_dicts: list[dict],
    ) -> None:
        """Loaded mappings have field values matching the input config.

        **Validates: Requirement 4.1**
        """
        router = ChannelRouter()
        router.load_from_config({"mappings": mapping_dicts})

        for entry in mapping_dicts:
            m = router.get_mapping_for_discord(entry["discord_channel_id"])
            assert m is not None

            assert m.discord_channel_id == entry["discord_channel_id"]
            assert m.irc is not None
            assert m.irc.server == entry["irc"]["server"]
            assert m.irc.channel == entry["irc"]["channel"]
            assert m.xmpp is not None
            assert m.xmpp.muc_jid == entry["xmpp"]["muc_jid"]
