"""Test relay routing logic."""


from bridge.events import MessageIn, MessageOut, message_in
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
        return isinstance(evt, MessageOut) and evt.target_origin == self._name

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
                    "irc": {"server": "irc.libera.chat", "channel": "#test", "port": 6667, "tls": False},
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
                    "irc": {"server": "irc.libera.chat", "channel": "#test", "port": 6667, "tls": False},
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        discord_adapter = MockAdapter("discord")
        bus.register(relay)
        bus.register(discord_adapter)

        # Act
        _, evt = message_in("irc", "irc.libera.chat/#test", "u1", "User", "Hello", "msg1")
        bus.publish("irc", evt)

        # Assert
        assert len(discord_adapter.received_events) == 1
        _, out_evt = discord_adapter.received_events[0]
        assert out_evt.target_origin == "discord"

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
        _, evt = message_in("xmpp", "test@conference.example.com", "u1", "User", "Hello", "msg1")
        bus.publish("xmpp", evt)

        # Assert
        assert len(discord_adapter.received_events) == 1

    def test_relay_does_not_echo_to_origin(self):
        # Arrange
        bus = Bus()
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
                    "irc": {"server": "irc.libera.chat", "channel": "#test", "port": 6667, "tls": False},
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
                    "irc": {"server": "irc.libera.chat", "channel": "#test", "port": 6667, "tls": False},
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
                    "irc": {"server": "irc.libera.chat", "channel": "#test", "port": 6667, "tls": False},
                }
            ]
        }
        router.load_from_config(config)
        relay = Relay(bus, router)
        irc_adapter = MockAdapter("irc")
        bus.register(relay)
        bus.register(irc_adapter)

        # Act
        _, evt = message_in("discord", "123", "user123", "TestUser", "Test message", "msg1", reply_to_id="msg0")
        bus.publish("discord", evt)

        # Assert
        _, out_evt = irc_adapter.received_events[0]
        assert out_evt.author_id == "user123"
        assert out_evt.author_display == "TestUser"
        assert out_evt.content == "Test message"
        assert out_evt.message_id == "msg1"
        assert out_evt.reply_to_id == "msg0"

    def test_relay_accepts_only_message_in(self):
        # Arrange
        bus = Bus()
        router = ChannelRouter()
        relay = Relay(bus, router)

        # Act & Assert
        assert relay.accept_event("discord", MessageIn("discord", "ch1", "u1", "User", "Hi", "msg1")) is True
        assert relay.accept_event("discord", MessageOut("irc", "ch1", "u1", "User", "Hi", "msg1")) is False
        assert relay.accept_event("discord", "not an event") is False
