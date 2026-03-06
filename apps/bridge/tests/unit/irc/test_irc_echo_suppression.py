"""Tests for IRC echo suppression (Requirement 17.1).

Verifies that the bridge recognises its own messages (echo-message, RELAYMSG,
puppet-sent) and suppresses them to prevent infinite relay loops.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from bridge.adapters.irc.handlers import (
    is_own_echo,
    is_puppet_echo,
    is_relaymsg_echo,
)
from cachetools import TTLCache

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(nickname: str = "bridge") -> MagicMock:
    """Create a minimal mock IRCClient with the fields echo checks need."""
    client = MagicMock()
    client.nickname = nickname
    client._puppet_nick_check = None
    client._recent_relaymsg_sends = TTLCache(maxsize=100, ttl=5)
    return client


# ---------------------------------------------------------------------------
# is_own_echo — unit tests
# ---------------------------------------------------------------------------


class TestIsOwnEcho:
    """Unit tests for the centralised is_own_echo() utility."""

    def test_own_nick_is_echo(self) -> None:
        client = _make_client("bridge")
        assert is_own_echo(client, "bridge", {}) is True

    def test_different_nick_not_echo(self) -> None:
        client = _make_client("bridge")
        assert is_own_echo(client, "alice", {}) is False

    def test_draft_relaymsg_tag_is_echo(self) -> None:
        client = _make_client("bridge")
        tags = {"draft/relaymsg": "bridge"}
        assert is_own_echo(client, "spoofed_nick", tags) is True

    def test_relaymsg_tag_is_echo(self) -> None:
        client = _make_client("bridge")
        tags = {"relaymsg": "bridge"}
        assert is_own_echo(client, "spoofed_nick", tags) is True

    def test_relaymsg_tag_different_nick_not_echo(self) -> None:
        client = _make_client("bridge")
        tags = {"draft/relaymsg": "other_bridge"}
        assert is_own_echo(client, "spoofed_nick", tags) is False

    def test_empty_tags_not_echo(self) -> None:
        client = _make_client("bridge")
        assert is_own_echo(client, "alice", {}) is False


# ---------------------------------------------------------------------------
# is_puppet_echo — unit tests
# ---------------------------------------------------------------------------


class TestIsPuppetEcho:
    """Unit tests for the puppet echo detection."""

    def test_puppet_nick_is_echo(self) -> None:
        client = _make_client("bridge")
        client._puppet_nick_check = lambda n: n in {"alice_d", "bob_d"}
        assert is_puppet_echo(client, "alice_d") is True

    def test_non_puppet_nick_not_echo(self) -> None:
        client = _make_client("bridge")
        client._puppet_nick_check = lambda n: n in {"alice_d", "bob_d"}
        assert is_puppet_echo(client, "charlie") is False

    def test_no_puppet_check_not_echo(self) -> None:
        client = _make_client("bridge")
        client._puppet_nick_check = None
        assert is_puppet_echo(client, "alice_d") is False


# ---------------------------------------------------------------------------
# is_relaymsg_echo — unit tests
# ---------------------------------------------------------------------------


class TestIsRelaymsgEcho:
    """Unit tests for the RELAYMSG TTLCache fallback echo detection."""

    def test_recent_send_is_echo(self) -> None:
        client = _make_client("bridge")
        client._recent_relaymsg_sends[("irc.example.com", "#test", "alice/d")] = None
        assert is_relaymsg_echo(client, "irc.example.com", "#test", "alice/d", {}) is True

    def test_no_recent_send_not_echo(self) -> None:
        client = _make_client("bridge")
        assert is_relaymsg_echo(client, "irc.example.com", "#test", "alice/d", {}) is False

    def test_different_channel_not_echo(self) -> None:
        client = _make_client("bridge")
        client._recent_relaymsg_sends[("irc.example.com", "#test", "alice/d")] = None
        assert is_relaymsg_echo(client, "irc.example.com", "#other", "alice/d", {}) is False

    def test_different_server_not_echo(self) -> None:
        client = _make_client("bridge")
        client._recent_relaymsg_sends[("irc.example.com", "#test", "alice/d")] = None
        assert is_relaymsg_echo(client, "other.example.com", "#test", "alice/d", {}) is False
