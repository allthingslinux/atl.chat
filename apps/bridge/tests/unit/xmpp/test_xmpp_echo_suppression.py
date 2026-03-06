"""Tests for XMPP echo suppression (Requirement 17.2).

Verifies that the bridge recognises its own MUC echoes (puppet-sent and
listener-sent messages) and suppresses them to prevent infinite relay loops.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from bridge.adapters.xmpp.handlers import (
    is_listener_nick,
    is_recent_echo,
    is_xmpp_echo,
    should_suppress_echo,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_comp(component_jid: str = "bridge.example.com") -> MagicMock:
    """Create a minimal mock XMPPComponent with the fields echo checks need."""
    comp = MagicMock()
    comp._component_jid = component_jid
    # _recent_sent_nicks behaves like a dict/TTLCache — support `in` operator
    comp._recent_sent_nicks = {}
    return comp


def _setup_muc_plugin(comp: MagicMock, jid_map: dict[tuple[str, str], str | None]) -> None:
    """Wire up the MUC plugin mock so get_jid_property returns from *jid_map*.

    *jid_map* maps ``(room_jid, nick)`` → real JID string (or ``None``).
    """
    muc = MagicMock()

    def _get_jid_property(room_jid: str, nick: str, prop: str):
        return jid_map.get((room_jid, nick))

    muc.get_jid_property = _get_jid_property
    comp.plugin = {"xep_0045": muc}


# ---------------------------------------------------------------------------
# is_xmpp_echo — unit tests
# ---------------------------------------------------------------------------


class TestIsXmppEcho:
    """Unit tests for the centralised is_xmpp_echo() utility."""

    def test_puppet_jid_same_domain_is_echo(self) -> None:
        comp = _make_comp("bridge.example.com")
        _setup_muc_plugin(
            comp,
            {
                ("room@muc.example.com", "alice"): "alice@bridge.example.com/res",
            },
        )
        assert is_xmpp_echo(comp, "room@muc.example.com", "alice") is True

    def test_external_user_different_domain_not_echo(self) -> None:
        comp = _make_comp("bridge.example.com")
        _setup_muc_plugin(
            comp,
            {
                ("room@muc.example.com", "bob"): "bob@users.example.com/client",
            },
        )
        assert is_xmpp_echo(comp, "room@muc.example.com", "bob") is False

    def test_jid_property_returns_none_not_echo(self) -> None:
        """When the MUC doesn't expose real JIDs, is_xmpp_echo returns False."""
        comp = _make_comp("bridge.example.com")
        _setup_muc_plugin(
            comp,
            {
                ("room@muc.example.com", "alice"): None,
            },
        )
        assert is_xmpp_echo(comp, "room@muc.example.com", "alice") is False

    def test_no_muc_plugin_not_echo(self) -> None:
        comp = _make_comp("bridge.example.com")
        comp.plugin = {}
        assert is_xmpp_echo(comp, "room@muc.example.com", "alice") is False

    def test_empty_nick_not_echo(self) -> None:
        comp = _make_comp("bridge.example.com")
        _setup_muc_plugin(comp, {})
        assert is_xmpp_echo(comp, "room@muc.example.com", "") is False

    def test_component_jid_with_at_sign(self) -> None:
        """Component JID like 'bridge@component.example.com' uses domain part."""
        comp = _make_comp("bridge@component.example.com")
        _setup_muc_plugin(
            comp,
            {
                ("room@muc.example.com", "puppet"): "puppet@component.example.com/res",
            },
        )
        assert is_xmpp_echo(comp, "room@muc.example.com", "puppet") is True

    def test_component_jid_without_at_sign(self) -> None:
        """Component JID like 'bridge.example.com' (no @) is used as-is for domain."""
        comp = _make_comp("bridge.example.com")
        _setup_muc_plugin(
            comp,
            {
                ("room@muc.example.com", "puppet"): "puppet@bridge.example.com/res",
            },
        )
        assert is_xmpp_echo(comp, "room@muc.example.com", "puppet") is True


# ---------------------------------------------------------------------------
# is_recent_echo — unit tests
# ---------------------------------------------------------------------------


class TestIsRecentEcho:
    """Unit tests for the fallback recent-sent-nicks echo detection."""

    def test_recent_nick_is_echo(self) -> None:
        comp = _make_comp()
        comp._recent_sent_nicks[("room@muc.example.com", "alice")] = None
        assert is_recent_echo(comp, "room@muc.example.com", "alice") is True

    def test_unknown_nick_not_echo(self) -> None:
        comp = _make_comp()
        assert is_recent_echo(comp, "room@muc.example.com", "bob") is False

    def test_different_room_not_echo(self) -> None:
        comp = _make_comp()
        comp._recent_sent_nicks[("room@muc.example.com", "alice")] = None
        assert is_recent_echo(comp, "other@muc.example.com", "alice") is False


# ---------------------------------------------------------------------------
# is_listener_nick — unit tests
# ---------------------------------------------------------------------------


class TestIsListenerNick:
    """Unit tests for the listener nick check."""

    def test_bridge_nick_is_listener(self) -> None:
        assert is_listener_nick("bridge") is True

    def test_other_nick_not_listener(self) -> None:
        assert is_listener_nick("alice") is False

    def test_empty_nick_not_listener(self) -> None:
        assert is_listener_nick("") is False


# ---------------------------------------------------------------------------
# should_suppress_echo — combined check
# ---------------------------------------------------------------------------


class TestShouldSuppressEcho:
    """Unit tests for the combined should_suppress_echo() utility."""

    def test_suppresses_puppet_echo_via_jid(self) -> None:
        comp = _make_comp("bridge.example.com")
        _setup_muc_plugin(
            comp,
            {
                ("room@muc.example.com", "puppet"): "puppet@bridge.example.com/res",
            },
        )
        assert should_suppress_echo(comp, "room@muc.example.com", "puppet") is True

    def test_suppresses_via_recent_nicks_fallback(self) -> None:
        comp = _make_comp("bridge.example.com")
        _setup_muc_plugin(
            comp,
            {
                ("room@muc.example.com", "puppet"): None,  # JID not exposed
            },
        )
        comp._recent_sent_nicks[("room@muc.example.com", "puppet")] = None
        assert should_suppress_echo(comp, "room@muc.example.com", "puppet") is True

    def test_suppresses_listener_nick(self) -> None:
        comp = _make_comp("bridge.example.com")
        _setup_muc_plugin(comp, {})
        assert should_suppress_echo(comp, "room@muc.example.com", "bridge") is True

    def test_does_not_suppress_external_user(self) -> None:
        comp = _make_comp("bridge.example.com")
        _setup_muc_plugin(
            comp,
            {
                ("room@muc.example.com", "alice"): "alice@users.example.com/client",
            },
        )
        assert should_suppress_echo(comp, "room@muc.example.com", "alice") is False

    def test_does_not_suppress_unknown_nick_no_fallback(self) -> None:
        comp = _make_comp("bridge.example.com")
        _setup_muc_plugin(
            comp,
            {
                ("room@muc.example.com", "alice"): None,
            },
        )
        # Not in _recent_sent_nicks either
        assert should_suppress_echo(comp, "room@muc.example.com", "alice") is False
