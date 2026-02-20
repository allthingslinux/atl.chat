"""Extended relay tests covering untested paths in relay.py."""

from __future__ import annotations

from unittest.mock import patch

from bridge.events import (
    MessageDeleteOut,
    MessageIn,
    MessageOut,
    ReactionOut,
    TypingOut,
    message_delete,
    message_in,
    reaction_in,
    typing_in,
)
from bridge.gateway.bus import Bus
from bridge.gateway.relay import Relay, _content_matches_filter, _transform_content
from bridge.gateway.router import ChannelRouter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _full_config():
    return {
        "mappings": [
            {
                "discord_channel_id": "123",
                "irc": {"server": "irc.libera.chat", "channel": "#test", "port": 6697, "tls": True},
                "xmpp": {"muc_jid": "room@conf.example.com"},
            }
        ]
    }


class Capture:
    def __init__(self, target_origin: str):
        self._target = target_origin
        self.events: list = []

    def accept_event(self, source, evt):
        return (
            isinstance(evt, (MessageOut, MessageDeleteOut, ReactionOut, TypingOut))
            and evt.target_origin == self._target
        )

    def push_event(self, source, evt):
        self.events.append(evt)


def _setup(config=None):
    bus = Bus()
    router = ChannelRouter()
    router.load_from_config(config or _full_config())
    relay = Relay(bus, router)
    bus.register(relay)
    discord = Capture("discord")
    irc = Capture("irc")
    xmpp = Capture("xmpp")
    bus.register(discord)
    bus.register(irc)
    bus.register(xmpp)
    return bus, discord, irc, xmpp


# ---------------------------------------------------------------------------
# _transform_content
# ---------------------------------------------------------------------------

class TestTransformContent:
    def test_discord_to_irc_strips_markdown(self):
        result = _transform_content("**bold**", "discord", "irc")
        assert result == "bold"

    def test_irc_to_discord_converts_bold(self):
        result = _transform_content("\x02bold\x02", "irc", "discord")
        assert result == "**bold**"

    def test_xmpp_to_discord_passthrough(self):
        result = _transform_content("hello", "xmpp", "discord")
        assert result == "hello"

    def test_discord_to_xmpp_passthrough(self):
        result = _transform_content("**bold**", "discord", "xmpp")
        assert result == "**bold**"

    def test_irc_to_xmpp_passthrough(self):
        result = _transform_content("\x02bold\x02", "irc", "xmpp")
        assert result == "\x02bold\x02"

    def test_xmpp_to_irc_passthrough(self):
        result = _transform_content("hello", "xmpp", "irc")
        assert result == "hello"


# ---------------------------------------------------------------------------
# _content_matches_filter
# ---------------------------------------------------------------------------

class TestContentMatchesFilter:
    def test_no_patterns_returns_false(self):
        with patch("bridge.gateway.relay.cfg") as mock_cfg:
            mock_cfg.content_filter_regex = []
            assert _content_matches_filter("anything") is False

    def test_matching_pattern_returns_true(self):
        with patch("bridge.gateway.relay.cfg") as mock_cfg:
            mock_cfg.content_filter_regex = [r"spam"]
            assert _content_matches_filter("this is spam") is True

    def test_non_matching_pattern_returns_false(self):
        with patch("bridge.gateway.relay.cfg") as mock_cfg:
            mock_cfg.content_filter_regex = [r"spam"]
            assert _content_matches_filter("clean message") is False

    def test_second_pattern_matches(self):
        with patch("bridge.gateway.relay.cfg") as mock_cfg:
            mock_cfg.content_filter_regex = [r"spam", r"blocked"]
            assert _content_matches_filter("this is blocked") is True

    def test_invalid_regex_skipped_no_crash(self):
        with patch("bridge.gateway.relay.cfg") as mock_cfg:
            mock_cfg.content_filter_regex = [r"[invalid", r"spam"]
            assert _content_matches_filter("spam") is True  # second pattern still works

    def test_empty_content_no_match(self):
        with patch("bridge.gateway.relay.cfg") as mock_cfg:
            mock_cfg.content_filter_regex = [r"spam"]
            assert _content_matches_filter("") is False


# ---------------------------------------------------------------------------
# IRC → XMPP routing
# ---------------------------------------------------------------------------

class TestIRCToXMPP:
    def test_irc_message_routes_to_xmpp(self):
        bus, _discord, _irc, xmpp = _setup()
        _, evt = message_in("irc", "irc.libera.chat/#test", "u1", "User", "hello", "m1")
        bus.publish("irc", evt)
        assert len(xmpp.events) == 1
        assert xmpp.events[0].content == "hello"
        assert xmpp.events[0].author_id == "u1"

    def test_irc_message_does_not_echo_to_irc(self):
        bus, _discord, irc, _xmpp = _setup()
        _, evt = message_in("irc", "irc.libera.chat/#test", "u1", "User", "hello", "m1")
        bus.publish("irc", evt)
        assert len(irc.events) == 0

    def test_irc_delete_routes_to_discord_and_xmpp(self):
        bus, discord, _irc, xmpp = _setup()
        _, evt = message_delete("irc", "irc.libera.chat/#test", "m1", author_id="u1")
        bus.publish("irc", evt)
        assert len(discord.events) == 1
        assert len(xmpp.events) == 1
        assert discord.events[0].message_id == "m1"
        assert xmpp.events[0].message_id == "m1"

    def test_irc_reaction_routes_to_discord_and_xmpp(self):
        bus, discord, _irc, xmpp = _setup()
        _, evt = reaction_in("irc", "irc.libera.chat/#test", "m1", "👍", "u1", "User")
        bus.publish("irc", evt)
        assert len(discord.events) == 1
        assert len(xmpp.events) == 1
        assert discord.events[0].emoji == "👍"

    def test_irc_typing_routes_to_discord_and_xmpp(self):
        bus, discord, _irc, xmpp = _setup()
        _, evt = typing_in("irc", "irc.libera.chat/#test", "u1")
        bus.publish("irc", evt)
        assert len(discord.events) == 1
        assert len(xmpp.events) == 1


# ---------------------------------------------------------------------------
# XMPP → IRC routing
# ---------------------------------------------------------------------------

class TestXMPPToIRC:
    def test_xmpp_message_routes_to_irc(self):
        bus, _discord, irc, _xmpp = _setup()
        _, evt = message_in("xmpp", "room@conf.example.com", "u1", "User", "hello", "m1")
        bus.publish("xmpp", evt)
        assert len(irc.events) == 1
        assert irc.events[0].content == "hello"

    def test_xmpp_message_does_not_echo_to_xmpp(self):
        bus, _discord, _irc, xmpp = _setup()
        _, evt = message_in("xmpp", "room@conf.example.com", "u1", "User", "hello", "m1")
        bus.publish("xmpp", evt)
        assert len(xmpp.events) == 0

    def test_xmpp_delete_routes_to_discord_and_irc(self):
        bus, discord, irc, _xmpp = _setup()
        _, evt = message_delete("xmpp", "room@conf.example.com", "m1", author_id="u1")
        bus.publish("xmpp", evt)
        assert len(discord.events) == 1
        assert len(irc.events) == 1

    def test_xmpp_reaction_routes_to_discord_and_irc(self):
        bus, discord, irc, _xmpp = _setup()
        _, evt = reaction_in("xmpp", "room@conf.example.com", "m1", "❤️", "u1", "User")
        bus.publish("xmpp", evt)
        assert len(discord.events) == 1
        assert len(irc.events) == 1
        assert irc.events[0].emoji == "❤️"

    def test_xmpp_typing_routes_to_discord_and_irc(self):
        bus, discord, irc, _xmpp = _setup()
        _, evt = typing_in("xmpp", "room@conf.example.com", "u1")
        bus.publish("xmpp", evt)
        assert len(discord.events) == 1
        assert len(irc.events) == 1


# ---------------------------------------------------------------------------
# No mapping for delete / reaction / typing
# ---------------------------------------------------------------------------

class TestNoMappingRouting:
    def test_delete_no_mapping_produces_no_output(self):
        bus, _discord, irc, xmpp = _setup()
        _, evt = message_delete("discord", "999", "m1")
        bus.publish("discord", evt)
        assert len(irc.events) == 0
        assert len(xmpp.events) == 0

    def test_reaction_no_mapping_produces_no_output(self):
        bus, _discord, irc, xmpp = _setup()
        _, evt = reaction_in("discord", "999", "m1", "👍", "u1", "User")
        bus.publish("discord", evt)
        assert len(irc.events) == 0
        assert len(xmpp.events) == 0

    def test_typing_no_mapping_produces_no_output(self):
        bus, _discord, irc, xmpp = _setup()
        _, evt = typing_in("discord", "999", "u1")
        bus.publish("discord", evt)
        assert len(irc.events) == 0
        assert len(xmpp.events) == 0

    def test_irc_delete_malformed_channel_id_produces_no_output(self):
        bus, discord, _irc, _xmpp = _setup()
        _, evt = message_delete("irc", "malformed", "m1")
        bus.publish("irc", evt)
        assert len(discord.events) == 0


# ---------------------------------------------------------------------------
# Outbound event field correctness
# ---------------------------------------------------------------------------

class TestOutboundFields:
    def test_message_out_raw_contains_origin(self):
        bus, _discord, irc, xmpp = _setup()
        _, evt = message_in("discord", "123", "u1", "User", "hi", "m1")
        bus.publish("discord", evt)
        assert irc.events[0].raw.get("origin") == "discord"
        assert xmpp.events[0].raw.get("origin") == "discord"

    def test_message_out_raw_is_edit_false_for_normal_message(self):
        bus, _discord, irc, _xmpp = _setup()
        _, evt = message_in("discord", "123", "u1", "User", "hi", "m1")
        bus.publish("discord", evt)
        assert irc.events[0].raw.get("is_edit") is False

    def test_message_out_raw_is_edit_true_for_edit(self):
        bus, _discord, irc, _xmpp = _setup()
        evt = MessageIn("discord", "123", "u1", "User", "edited", "m1", is_edit=True,
                        raw={"replace_id": "orig-1"})
        bus.publish("discord", evt)
        assert irc.events[0].raw.get("is_edit") is True
        assert irc.events[0].raw.get("replace_id") == "orig-1"

    def test_avatar_url_preserved_in_message_out(self):
        bus, _discord, irc, xmpp = _setup()
        evt = MessageIn("discord", "123", "u1", "User", "hi", "m1",
                        avatar_url="https://cdn.example.com/avatar.png")
        bus.publish("discord", evt)
        assert irc.events[0].avatar_url == "https://cdn.example.com/avatar.png"
        assert xmpp.events[0].avatar_url == "https://cdn.example.com/avatar.png"

    def test_delete_out_author_id_preserved(self):
        bus, _discord, irc, xmpp = _setup()
        _, evt = message_delete("discord", "123", "m1", author_id="user-abc")
        bus.publish("discord", evt)
        assert irc.events[0].author_id == "user-abc"
        assert xmpp.events[0].author_id == "user-abc"

    def test_reaction_out_uses_discord_channel_id(self):
        bus, _discord, irc, xmpp = _setup()
        _, evt = reaction_in("discord", "123", "m1", "👍", "u1", "User")
        bus.publish("discord", evt)
        assert irc.events[0].channel_id == "123"
        assert xmpp.events[0].channel_id == "123"

    def test_typing_out_uses_discord_channel_id(self):
        bus, _discord, irc, xmpp = _setup()
        _, evt = typing_in("discord", "123", "u1")
        bus.publish("discord", evt)
        assert irc.events[0].channel_id == "123"
        assert xmpp.events[0].channel_id == "123"


# ---------------------------------------------------------------------------
# push_event with unknown event type
# ---------------------------------------------------------------------------

class TestPushEventUnknown:
    def test_unknown_event_type_produces_no_output(self):
        bus, discord, irc, xmpp = _setup()
        bus.publish("discord", object())
        assert len(irc.events) == 0
        assert len(xmpp.events) == 0
        assert len(discord.events) == 0

    def test_relay_accept_event_rejects_unknown(self):
        bus = Bus()
        router = ChannelRouter()
        relay = Relay(bus, router)
        assert relay.accept_event("discord", object()) is False
        assert relay.accept_event("discord", "string") is False
        assert relay.accept_event("discord", 42) is False


# ---------------------------------------------------------------------------
# IRC-only mapping (no XMPP)
# ---------------------------------------------------------------------------

class TestIRCOnlyMapping:
    def test_discord_message_only_goes_to_irc(self):
        bus = Bus()
        router = ChannelRouter()
        router.load_from_config({
            "mappings": [{
                "discord_channel_id": "123",
                "irc": {"server": "s", "channel": "#c", "port": 6667, "tls": False},
            }]
        })
        relay = Relay(bus, router)
        bus.register(relay)
        irc = Capture("irc")
        xmpp = Capture("xmpp")
        bus.register(irc)
        bus.register(xmpp)

        _, evt = message_in("discord", "123", "u1", "User", "hi", "m1")
        bus.publish("discord", evt)

        assert len(irc.events) == 1
        assert len(xmpp.events) == 0
