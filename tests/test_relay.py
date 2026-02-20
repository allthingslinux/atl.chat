"""Test relay routing logic."""

from unittest.mock import patch

from bridge.events import (
    MessageDelete,
    MessageDeleteOut,
    MessageIn,
    MessageOut,
    ReactionIn,
    ReactionOut,
    TypingIn,
    TypingOut,
    message_delete,
    message_in,
    reaction_in,
    typing_in,
)
from bridge.gateway.bus import Bus
from bridge.gateway.relay import Relay
from bridge.gateway.router import ChannelRouter


class MockAdapter:
    """Mock adapter for testing."""

    def __init__(self, name: str):
        self._name = name
        self.received_events = []

    @property
    def name(self) -> str:
        return self._name

    def accept_event(self, source: str, evt: object) -> bool:
        if isinstance(evt, MessageOut) and evt.target_origin == self._name:
            return True
        if isinstance(evt, MessageDeleteOut) and evt.target_origin == self._name:
            return True
        if isinstance(evt, ReactionOut) and evt.target_origin == self._name:
            return True
        return isinstance(evt, TypingOut) and evt.target_origin == self._name

    def push_event(self, source: str, evt: object) -> None:
        self.received_events.append((source, evt))


class TestRelay:
    """Test relay routing logic."""

    def test_relay_discord_to_irc(self):
        # Arrange
        bus = Bus()
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
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockAdapter("irc")
        bus.register(relay)
        bus.register(irc_adapter)

        # Act
        _, evt = message_in("discord", "123", "u1", "User", "Hello", "msg1")
        bus.publish("discord", evt)

        # Assert
        assert len(irc_adapter.received_events) == 1
        _, out_evt = irc_adapter.received_events[0]
        assert isinstance(out_evt, MessageOut)
        assert out_evt.target_origin == "irc"
        assert out_evt.content == "Hello"

    def test_relay_irc_to_discord(self):
        # Arrange
        bus = Bus()
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
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        discord_adapter = MockAdapter("discord")
        bus.register(relay)
        bus.register(discord_adapter)

        # Act
        _, evt = message_in("irc", "irc.libera.chat/#test", "u1", "User", "Hello from IRC", "msg1")
        bus.publish("irc", evt)

        # Assert
        assert len(discord_adapter.received_events) == 1
        _, out_evt = discord_adapter.received_events[0]
        assert out_evt.target_origin == "discord"
        assert out_evt.content == "Hello from IRC"
        assert out_evt.author_id == "u1"

    def test_relay_xmpp_to_discord(self):
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "xmpp": {"muc_jid": "test@conference.example.com"},
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        discord_adapter = MockAdapter("discord")
        bus.register(relay)
        bus.register(discord_adapter)

        # Act
        _, evt = message_in(
            "xmpp", "test@conference.example.com", "u1", "User", "Hello from XMPP", "msg1"
        )
        bus.publish("xmpp", evt)

        # Assert
        assert len(discord_adapter.received_events) == 1
        _, out_evt = discord_adapter.received_events[0]
        assert out_evt.target_origin == "discord"
        assert out_evt.content == "Hello from XMPP"
        assert out_evt.author_id == "u1"

    def test_relay_does_not_echo_to_origin(self):
        # Arrange
        bus = Bus()
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
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        discord_adapter = MockAdapter("discord")
        irc_adapter = MockAdapter("irc")
        bus.register(relay)
        bus.register(discord_adapter)
        bus.register(irc_adapter)

        # Act
        _, evt = message_in("discord", "123", "u1", "User", "Hello", "msg1")
        bus.publish("discord", evt)

        # Assert
        assert len(discord_adapter.received_events) == 0
        assert len(irc_adapter.received_events) == 1

    def test_relay_to_all_targets(self):
        # Arrange
        bus = Bus()
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
        relay = Relay(bus, router)
        irc_adapter = MockAdapter("irc")
        xmpp_adapter = MockAdapter("xmpp")
        bus.register(relay)
        bus.register(irc_adapter)
        bus.register(xmpp_adapter)

        # Act
        _, evt = message_in("discord", "123", "u1", "User", "Hello", "msg1")
        bus.publish("discord", evt)

        # Assert
        assert len(irc_adapter.received_events) == 1
        assert len(xmpp_adapter.received_events) == 1

    def test_relay_ignores_unmapped_channel(self):
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        config = {"mappings": [{"discord_channel_id": "123"}]}
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockAdapter("irc")
        bus.register(relay)
        bus.register(irc_adapter)

        # Act
        _, evt = message_in("discord", "999", "u1", "User", "Hello", "msg1")
        bus.publish("discord", evt)

        # Assert
        assert len(irc_adapter.received_events) == 0

    def test_relay_skips_missing_targets(self):
        # Arrange
        bus = Bus()
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
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockAdapter("irc")
        xmpp_adapter = MockAdapter("xmpp")
        bus.register(relay)
        bus.register(irc_adapter)
        bus.register(xmpp_adapter)

        # Act
        _, evt = message_in("discord", "123", "u1", "User", "Hello", "msg1")
        bus.publish("discord", evt)

        # Assert
        assert len(irc_adapter.received_events) == 1
        assert len(xmpp_adapter.received_events) == 0  # No XMPP mapping

    def test_relay_preserves_message_content(self):
        # Arrange
        bus = Bus()
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
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockAdapter("irc")
        bus.register(relay)
        bus.register(irc_adapter)

        # Act
        _, evt = message_in(
            "discord", "123", "user123", "TestUser", "Test message", "msg1", reply_to_id="msg0"
        )
        bus.publish("discord", evt)

        # Assert
        _, out_evt = irc_adapter.received_events[0]
        assert out_evt.author_id == "user123"
        assert out_evt.author_display == "TestUser"
        assert out_evt.content == "Test message"
        assert out_evt.message_id == "msg1"
        assert out_evt.reply_to_id == "msg0"

    def test_relay_strips_discord_markdown_for_irc(self):
        """Discord -> IRC: strip **bold** and *italic* to plain text."""
        bus = Bus()
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
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockAdapter("irc")
        bus.register(relay)
        bus.register(irc_adapter)

        _, evt = message_in("discord", "123", "u1", "User", "**bold** and *italic*", "msg1")
        bus.publish("discord", evt)

        _, out_evt = irc_adapter.received_events[0]
        assert out_evt.content == "bold and italic"

    def test_relay_converts_irc_codes_for_discord(self):
        """IRC -> Discord: convert IRC bold to **markdown**."""
        bus = Bus()
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
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        discord_adapter = MockAdapter("discord")
        bus.register(relay)
        bus.register(discord_adapter)

        bold = "\x02"
        _, evt = message_in(
            "irc", "irc.libera.chat/#test", "u1", "User", f"{bold}bold{bold}", "msg1"
        )
        bus.publish("irc", evt)

        _, out_evt = discord_adapter.received_events[0]
        assert out_evt.content == "**bold**"

    def test_relay_accepts_only_message_in(self):
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        relay = Relay(bus, router)

        # Act & Assert
        assert (
            relay.accept_event("discord", MessageIn("discord", "ch1", "u1", "User", "Hi", "msg1"))
            is True
        )
        assert (
            relay.accept_event("discord", MessageOut("irc", "ch1", "u1", "User", "Hi", "msg1"))
            is False
        )
        assert relay.accept_event("discord", "not an event") is False

    def test_relay_accepts_message_delete_reaction_typing(self):
        bus = Bus()
        router = ChannelRouter()
        relay = Relay(bus, router)
        assert relay.accept_event("discord", MessageDelete("discord", "123", "m1", "u1")) is True
        assert (
            relay.accept_event("discord", ReactionIn("discord", "123", "m1", "👍", "u1", "User"))
            is True
        )
        assert relay.accept_event("discord", TypingIn("discord", "123", "u1")) is True

    def test_content_filter_skips_matching_messages(self):
        """Messages matching content_filter_regex are not relayed."""
        bus = Bus()
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
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockAdapter("irc")
        bus.register(relay)
        bus.register(irc_adapter)

        with patch("bridge.gateway.relay.cfg") as mock_cfg:
            mock_cfg.content_filter_regex = [r"spam", r"\bblocked\b"]
            _, evt = message_in("discord", "123", "u1", "User", "this is spam", "msg1")
            bus.publish("discord", evt)

        assert len(irc_adapter.received_events) == 0

    def test_content_filter_allows_non_matching_messages(self):
        with patch("bridge.gateway.relay.cfg") as mock_cfg:
            mock_cfg.content_filter_regex = [r"spam"]
            bus = Bus()
            router = ChannelRouter()
            router.load_from_config(
                {
                    "mappings": [
                        {
                            "discord_channel_id": "123",
                            "irc": {"server": "s", "channel": "#c", "port": 6667, "tls": False},
                        }
                    ]
                }
            )
            relay = Relay(bus, router)
            irc_adapter = MockAdapter("irc")
            bus.register(relay)
            bus.register(irc_adapter)
            _, evt = message_in("discord", "123", "u1", "User", "hello world", "msg1")
            bus.publish("discord", evt)
        assert len(irc_adapter.received_events) == 1

    def test_relay_routes_message_delete_to_targets(self):
        """Discord message delete produces MessageDeleteOut to IRC and XMPP."""
        bus = Bus()
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
                    "xmpp": {"muc_jid": "room@conference.example.com"},
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockAdapter("irc")
        xmpp_adapter = MockAdapter("xmpp")
        bus.register(relay)
        bus.register(irc_adapter)
        bus.register(xmpp_adapter)

        _, evt = message_delete("discord", "123", "msg-999", author_id="user123")
        bus.publish("discord", evt)

        irc_deletes = [e for _, e in irc_adapter.received_events if isinstance(e, MessageDeleteOut)]
        xmpp_deletes = [
            e for _, e in xmpp_adapter.received_events if isinstance(e, MessageDeleteOut)
        ]
        assert len(irc_deletes) == 1
        assert irc_deletes[0].message_id == "msg-999"
        assert len(xmpp_deletes) == 1

    def test_relay_routes_reactions(self):
        """Discord reaction produces ReactionOut to IRC and XMPP."""
        bus = Bus()
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {"server": "s", "channel": "#c", "port": 6667, "tls": False},
                    "xmpp": {"muc_jid": "room@conf.example.com"},
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockAdapter("irc")
        xmpp_adapter = MockAdapter("xmpp")
        bus.register(relay)
        bus.register(irc_adapter)
        bus.register(xmpp_adapter)

        _, evt = reaction_in("discord", "123", "msg-1", "👍", "user1", "User")
        bus.publish("discord", evt)

        irc_rx = [e for _, e in irc_adapter.received_events if isinstance(e, ReactionOut)]
        xmpp_rx = [e for _, e in xmpp_adapter.received_events if isinstance(e, ReactionOut)]
        assert len(irc_rx) == 1
        assert irc_rx[0].emoji == "👍"
        assert len(xmpp_rx) == 1

    def test_relay_routes_typing(self):
        """Discord typing produces TypingOut to IRC and XMPP."""
        bus = Bus()
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {"server": "s", "channel": "#c", "port": 6667, "tls": False},
                    "xmpp": {"muc_jid": "room@conf.example.com"},
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockAdapter("irc")
        xmpp_adapter = MockAdapter("xmpp")
        bus.register(relay)
        bus.register(irc_adapter)
        bus.register(xmpp_adapter)

        _, evt = typing_in("discord", "123", "user1")
        bus.publish("discord", evt)

        irc_typing = [e for _, e in irc_adapter.received_events if isinstance(e, TypingOut)]
        xmpp_typing = [e for _, e in xmpp_adapter.received_events if isinstance(e, TypingOut)]
        assert len(irc_typing) == 1
        assert len(xmpp_typing) == 1

    def test_relay_passes_is_edit_and_replace_id_for_corrections(self):
        """XMPP correction (is_edit, replace_id) is passed through to Discord target."""
        bus = Bus()
        router = ChannelRouter()
        config = {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "xmpp": {"muc_jid": "room@conference.example.com"},
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        discord_adapter = MockAdapter("discord")
        bus.register(relay)
        bus.register(discord_adapter)

        evt = MessageIn(
            origin="xmpp",
            channel_id="room@conference.example.com",
            author_id="u@ex.com",
            author_display="User",
            content="corrected",
            message_id="corr-2",
            is_edit=True,
            raw={"replace_id": "orig-1"},
        )
        bus.publish("xmpp", evt)

        msgs = [e for _, e in discord_adapter.received_events if isinstance(e, MessageOut)]
        assert len(msgs) == 1
        assert msgs[0].raw.get("is_edit") is True
        assert msgs[0].raw.get("replace_id") == "orig-1"
        assert msgs[0].raw.get("origin") == "xmpp"
