"""Test event types and factories."""


from bridge.events import (
    ConfigReload,
    Join,
    MessageDelete,
    MessageDeleteOut,
    MessageIn,
    MessageOut,
    Part,
    Quit,
    ReactionIn,
    ReactionOut,
    TypingIn,
    TypingOut,
    config_reload,
    join,
    message_delete,
    message_delete_out,
    message_in,
    message_out,
    part,
    quit,
    reaction_in,
    reaction_out,
    typing_in,
    typing_out,
)


class TestMessageInEvent:
    """Test MessageIn event creation."""

    def test_message_in_factory(self):
        event_type, evt = message_in(
            origin="discord",
            channel_id="123",
            author_id="user1",
            author_display="TestUser",
            content="Hello",
            message_id="msg1",
        )
        assert event_type == "message_in"
        assert isinstance(evt, MessageIn)
        assert evt.origin == "discord"
        assert evt.channel_id == "123"
        assert evt.author_id == "user1"
        assert evt.author_display == "TestUser"
        assert evt.content == "Hello"
        assert evt.message_id == "msg1"
        assert evt.reply_to_id is None
        assert evt.is_edit is False
        assert evt.is_action is False

    def test_message_in_with_reply(self):
        _, evt = message_in("irc", "ch1", "u1", "User", "Reply", "msg2", reply_to_id="msg1")
        assert evt.reply_to_id == "msg1"

    def test_message_in_edit(self):
        _, evt = message_in("xmpp", "ch1", "u1", "User", "Edited", "msg1", is_edit=True)
        assert evt.is_edit is True

    def test_message_in_action(self):
        _, evt = message_in("irc", "ch1", "u1", "User", "does something", "msg1", is_action=True)
        assert evt.is_action is True

    def test_message_in_avatar_url(self):
        _, evt = message_in("discord", "ch1", "u1", "User", "hi", "msg1", avatar_url="https://example.com/a.png")
        assert evt.avatar_url == "https://example.com/a.png"

    def test_message_in_raw_none_defaults_to_empty_dict(self):
        _, evt = message_in("discord", "ch1", "u1", "User", "hi", "msg1", raw=None)
        assert evt.raw == {}

    def test_message_in_raw_passed_through(self):
        _, evt = message_in("discord", "ch1", "u1", "User", "hi", "msg1", raw={"key": "val"})
        assert evt.raw == {"key": "val"}

    def test_message_in_type_attribute(self):
        assert message_in.TYPE == "message_in"


class TestMessageOutEvent:
    """Test MessageOut event creation."""

    def test_message_out_factory(self):
        event_type, evt = message_out(
            target_origin="discord",
            channel_id="123",
            author_id="user1",
            author_display="TestUser",
            content="Hello",
            message_id="msg1",
        )
        assert event_type == "message_out"
        assert isinstance(evt, MessageOut)
        assert evt.target_origin == "discord"
        assert evt.content == "Hello"
        assert evt.reply_to_id is None
        assert evt.avatar_url is None

    def test_message_out_reply_to_id_and_avatar(self):
        _, evt = message_out(
            "irc", "ch1", "u1", "User", "hi", "msg1",
            reply_to_id="orig", avatar_url="https://example.com/a.png",
        )
        assert evt.reply_to_id == "orig"
        assert evt.avatar_url == "https://example.com/a.png"

    def test_message_out_raw_none_defaults_to_empty_dict(self):
        _, evt = message_out("discord", "ch1", "u1", "User", "hi", "msg1", raw=None)
        assert evt.raw == {}

    def test_message_out_type_attribute(self):
        assert message_out.TYPE == "message_out"


class TestJoinEvent:
    """Test Join event creation."""

    def test_join_factory(self):
        event_type, evt = join(origin="irc", channel_id="ch1", user_id="user1", display="TestUser")
        assert event_type == "join"
        assert isinstance(evt, Join)
        assert evt.origin == "irc"
        assert evt.channel_id == "ch1"
        assert evt.user_id == "user1"
        assert evt.display == "TestUser"


class TestPartEvent:
    """Test Part event creation."""

    def test_part_factory(self):
        event_type, evt = part(origin="irc", channel_id="ch1", user_id="user1", display="TestUser")
        assert event_type == "part"
        assert isinstance(evt, Part)
        assert evt.reason is None

    def test_part_with_reason(self):
        _, evt = part("irc", "ch1", "user1", "TestUser", reason="Leaving")
        assert evt.reason == "Leaving"


class TestQuitEvent:
    """Test Quit event creation."""

    def test_quit_factory(self):
        event_type, evt = quit(origin="irc", user_id="user1", display="TestUser")
        assert event_type == "quit"
        assert isinstance(evt, Quit)
        assert evt.reason is None

    def test_quit_with_reason(self):
        _, evt = quit("irc", "user1", "TestUser", reason="Connection lost")
        assert evt.reason == "Connection lost"


class TestConfigReloadEvent:
    """Test ConfigReload event creation."""

    def test_config_reload_factory(self):
        event_type, evt = config_reload()
        assert event_type == "config_reload"
        assert isinstance(evt, ConfigReload)


class TestMessageDeleteEvent:
    def test_message_delete_factory(self):
        event_type, evt = message_delete("discord", "ch1", "msg1")
        assert event_type == "message_delete"
        assert isinstance(evt, MessageDelete)
        assert evt.origin == "discord"
        assert evt.channel_id == "ch1"
        assert evt.message_id == "msg1"
        assert evt.author_id == ""

    def test_message_delete_with_author_id(self):
        _, evt = message_delete("xmpp", "ch1", "msg1", author_id="user@example.com")
        assert evt.author_id == "user@example.com"

    def test_message_delete_out_factory(self):
        event_type, evt = message_delete_out("irc", "ch1", "msg1")
        assert event_type == "message_delete_out"
        assert isinstance(evt, MessageDeleteOut)
        assert evt.target_origin == "irc"
        assert evt.channel_id == "ch1"
        assert evt.message_id == "msg1"
        assert evt.author_id == ""

    def test_message_delete_out_with_author_id(self):
        _, evt = message_delete_out("xmpp", "ch1", "msg1", author_id="user@example.com")
        assert evt.author_id == "user@example.com"


class TestReactionEvents:
    def test_reaction_in_factory(self):
        event_type, evt = reaction_in("discord", "ch1", "msg1", "👍", "u1", "User")
        assert event_type == "reaction_in"
        assert isinstance(evt, ReactionIn)
        assert evt.origin == "discord"
        assert evt.channel_id == "ch1"
        assert evt.message_id == "msg1"
        assert evt.emoji == "👍"
        assert evt.author_id == "u1"
        assert evt.author_display == "User"

    def test_reaction_out_factory(self):
        event_type, evt = reaction_out("irc", "ch1", "msg1", "❤️", "u1", "User")
        assert event_type == "reaction_out"
        assert isinstance(evt, ReactionOut)
        assert evt.target_origin == "irc"
        assert evt.emoji == "❤️"
        assert evt.author_display == "User"


class TestTypingEvents:
    def test_typing_in_factory(self):
        event_type, evt = typing_in("discord", "ch1", "u1")
        assert event_type == "typing_in"
        assert isinstance(evt, TypingIn)
        assert evt.origin == "discord"
        assert evt.channel_id == "ch1"
        assert evt.user_id == "u1"

    def test_typing_out_factory(self):
        event_type, evt = typing_out("irc", "ch1")
        assert event_type == "typing_out"
        assert isinstance(evt, TypingOut)
        assert evt.target_origin == "irc"
        assert evt.channel_id == "ch1"


class TestRawFieldIsolation:
    """Verify raw field defaults don't share mutable state between instances."""

    def test_message_in_raw_not_shared(self):
        _, evt1 = message_in("discord", "ch1", "u1", "User", "hi", "msg1")
        _, evt2 = message_in("discord", "ch1", "u1", "User", "hi", "msg2")
        evt1.raw["key"] = "val"
        assert "key" not in evt2.raw

    def test_message_out_raw_not_shared(self):
        _, evt1 = message_out("discord", "ch1", "u1", "User", "hi", "msg1")
        _, evt2 = message_out("discord", "ch1", "u1", "User", "hi", "msg2")
        evt1.raw["key"] = "val"
        assert "key" not in evt2.raw
