"""Tests for Join, Part, and Quit events."""

from __future__ import annotations

import pytest

from bridge.events import Join, Part, Quit


class TestJoinEvents:
    """Test Join event handling."""

    def test_join_event_creation(self):
        # Act
        event = Join(
            origin="irc",
            channel_id="#test",
            user_id="user!user@host",
            display="user",
        )

        # Assert
        assert event.origin == "irc"
        assert event.channel_id == "#test"
        assert event.user_id == "user!user@host"
        assert event.display == "user"

    def test_join_from_different_origins(self):
        # Arrange
        origins = [
            ("discord", "123456789", "987654321", "User"),
            ("irc", "#test", "user!user@host", "user"),
            ("xmpp", "room@conference.example.com", "user@example.com", "user"),
        ]

        # Act & Assert
        for origin, channel_id, user_id, display in origins:
            event = Join(
                origin=origin,
                channel_id=channel_id,
                user_id=user_id,
                display=display,
            )
            assert event.origin == origin
            assert event.channel_id == channel_id


class TestPartEvents:
    """Test Part event handling."""

    def test_part_event_without_reason(self):
        # Act
        event = Part(
            origin="irc",
            channel_id="#test",
            user_id="user!user@host",
            display="user",
        )

        # Assert
        assert event.origin == "irc"
        assert event.channel_id == "#test"
        assert event.user_id == "user!user@host"
        assert event.reason is None

    def test_part_event_with_reason(self):
        # Act
        event = Part(
            origin="irc",
            channel_id="#test",
            user_id="user!user@host",
            display="user",
            reason="Going to lunch",
        )

        # Assert
        assert event.reason == "Going to lunch"

    def test_part_from_xmpp_muc(self):
        # Act
        event = Part(
            origin="xmpp",
            channel_id="room@conference.example.com",
            user_id="user@example.com",
            display="user",
            reason="Disconnected",
        )

        # Assert
        assert event.origin == "xmpp"
        assert event.channel_id == "room@conference.example.com"
        assert event.reason == "Disconnected"


class TestQuitEvents:
    """Test Quit event handling."""

    def test_quit_event_without_reason(self):
        # Act
        event = Quit(
            origin="irc",
            user_id="user!user@host",
            display="user",
        )

        # Assert
        assert event.origin == "irc"
        assert event.user_id == "user!user@host"
        assert event.reason is None

    def test_quit_event_with_reason(self):
        # Act
        event = Quit(
            origin="irc",
            user_id="user!user@host",
            display="user",
            reason="Connection reset by peer",
        )

        # Assert
        assert event.reason == "Connection reset by peer"

    def test_quit_affects_all_channels(self):
        # Arrange - Quit doesn't have channel_id, affects all channels
        event = Quit(
            origin="irc",
            user_id="user!user@host",
            display="user",
            reason="Ping timeout",
        )

        # Assert
        assert not hasattr(event, "channel_id")
        assert event.user_id == "user!user@host"

    def test_quit_from_xmpp(self):
        # Act
        event = Quit(
            origin="xmpp",
            user_id="user@example.com",
            display="user",
            reason="Client disconnected",
        )

        # Assert
        assert event.origin == "xmpp"
        assert event.user_id == "user@example.com"


class TestPresenceEventComparison:
    """Test comparing different presence events."""

    def test_join_and_part_same_user(self):
        # Arrange
        join = Join(
            origin="irc",
            channel_id="#test",
            user_id="user!user@host",
            display="user",
        )
        part = Part(
            origin="irc",
            channel_id="#test",
            user_id="user!user@host",
            display="user",
        )

        # Assert
        assert join.user_id == part.user_id
        assert join.channel_id == part.channel_id
        assert type(join) != type(part)

    def test_part_and_quit_different_scope(self):
        # Arrange
        part = Part(
            origin="irc",
            channel_id="#test",
            user_id="user!user@host",
            display="user",
        )
        quit_event = Quit(
            origin="irc",
            user_id="user!user@host",
            display="user",
        )

        # Assert
        assert part.user_id == quit_event.user_id
        assert hasattr(part, "channel_id")
        assert not hasattr(quit_event, "channel_id")
