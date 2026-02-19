"""Test event types and factories."""


from bridge.events import (
    ConfigReload,
    Join,
    MessageIn,
    MessageOut,
    Part,
    Quit,
    config_reload,
    join,
    message_in,
    message_out,
    part,
    quit,
)


class TestMessageInEvent:
    """Test MessageIn event creation."""

    def test_message_in_factory(self):
        # Arrange
        origin = "discord"
        channel_id = "123"
        author_id = "user1"
        author_display = "TestUser"
        content = "Hello"
        message_id = "msg1"

        # Act
        event_type, evt = message_in(
            origin=origin,
            channel_id=channel_id,
            author_id=author_id,
            author_display=author_display,
            content=content,
            message_id=message_id,
        )

        # Assert
        assert event_type == "message_in"
        assert isinstance(evt, MessageIn)
        assert evt.origin == origin
        assert evt.channel_id == channel_id
        assert evt.author_id == author_id
        assert evt.author_display == author_display
        assert evt.content == content
        assert evt.message_id == message_id
        assert evt.reply_to_id is None
        assert evt.is_edit is False
        assert evt.is_action is False

    def test_message_in_with_reply(self):
        # Arrange & Act
        _, evt = message_in(
            origin="irc",
            channel_id="ch1",
            author_id="u1",
            author_display="User",
            content="Reply",
            message_id="msg2",
            reply_to_id="msg1",
        )

        # Assert
        assert evt.reply_to_id == "msg1"

    def test_message_in_edit(self):
        # Arrange & Act
        _, evt = message_in(
            origin="xmpp",
            channel_id="ch1",
            author_id="u1",
            author_display="User",
            content="Edited",
            message_id="msg1",
            is_edit=True,
        )

        # Assert
        assert evt.is_edit is True

    def test_message_in_action(self):
        # Arrange & Act
        _, evt = message_in(
            origin="irc",
            channel_id="ch1",
            author_id="u1",
            author_display="User",
            content="does something",
            message_id="msg1",
            is_action=True,
        )

        # Assert
        assert evt.is_action is True


class TestMessageOutEvent:
    """Test MessageOut event creation."""

    def test_message_out_factory(self):
        # Arrange & Act
        event_type, evt = message_out(
            target_origin="discord",
            channel_id="123",
            author_id="user1",
            author_display="TestUser",
            content="Hello",
            message_id="msg1",
        )

        # Assert
        assert event_type == "message_out"
        assert isinstance(evt, MessageOut)
        assert evt.target_origin == "discord"
        assert evt.content == "Hello"


class TestJoinEvent:
    """Test Join event creation."""

    def test_join_factory(self):
        # Arrange & Act
        event_type, evt = join(
            origin="irc",
            channel_id="ch1",
            user_id="user1",
            display="TestUser",
        )

        # Assert
        assert event_type == "join"
        assert isinstance(evt, Join)
        assert evt.origin == "irc"
        assert evt.channel_id == "ch1"
        assert evt.user_id == "user1"
        assert evt.display == "TestUser"


class TestPartEvent:
    """Test Part event creation."""

    def test_part_factory(self):
        # Arrange & Act
        event_type, evt = part(
            origin="irc",
            channel_id="ch1",
            user_id="user1",
            display="TestUser",
        )

        # Assert
        assert event_type == "part"
        assert isinstance(evt, Part)
        assert evt.reason is None

    def test_part_with_reason(self):
        # Arrange & Act
        _, evt = part(
            origin="irc",
            channel_id="ch1",
            user_id="user1",
            display="TestUser",
            reason="Leaving",
        )

        # Assert
        assert evt.reason == "Leaving"


class TestQuitEvent:
    """Test Quit event creation."""

    def test_quit_factory(self):
        # Arrange & Act
        event_type, evt = quit(
            origin="irc",
            user_id="user1",
            display="TestUser",
        )

        # Assert
        assert event_type == "quit"
        assert isinstance(evt, Quit)
        assert evt.reason is None

    def test_quit_with_reason(self):
        # Arrange & Act
        _, evt = quit(
            origin="irc",
            user_id="user1",
            display="TestUser",
            reason="Connection lost",
        )

        # Assert
        assert evt.reason == "Connection lost"


class TestConfigReloadEvent:
    """Test ConfigReload event creation."""

    def test_config_reload_factory(self):
        # Arrange & Act
        event_type, evt = config_reload()

        # Assert
        assert event_type == "config_reload"
        assert isinstance(evt, ConfigReload)
