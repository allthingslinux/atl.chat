"""Tests for MUC status code handling (Requirements 26.1-26.5).

Verifies that the XMPP adapter correctly handles MUC presence stanzas
with status codes for self-presence, nick modification, bans, kicks,
and removal/shutdown scenarios.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from xml.etree.ElementTree import Element, SubElement

from bridge.adapters.xmpp.handlers import (
    MUC_USER_NS,
    _extract_nick_from_presence,
    _extract_room_jid,
    _extract_status_codes,
    _remove_puppet_entries,
    on_muc_presence,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_comp(component_jid: str = "bridge.example.com", auto_rejoin: bool = True) -> MagicMock:
    """Create a minimal mock XMPPComponent for MUC status code tests."""
    comp = MagicMock()
    comp._component_jid = component_jid
    comp._puppets_joined = set()
    comp._banned_rooms = set()
    comp._auto_rejoin = auto_rejoin
    comp._confirmed_mucs = set()
    # MUC plugin mock for rejoin
    muc = MagicMock()
    muc.join_muc_wait = AsyncMock()
    comp.plugin = {"xep_0045": muc}
    return comp


def _make_presence(from_jid: str, status_codes: list[int], ptype: str = "available") -> MagicMock:
    """Build a mock presence stanza with MUC status codes."""
    presence = MagicMock()
    presence.get = MagicMock(side_effect=lambda key, default="": from_jid if key == "from" else default)

    # Build real XML for status code extraction
    root = Element("presence")
    root.set("from", from_jid)
    root.set("type", ptype)
    x_elem = SubElement(root, f"{{{MUC_USER_NS}}}x")
    for code in status_codes:
        status_el = SubElement(x_elem, f"{{{MUC_USER_NS}}}status")
        status_el.set("code", str(code))
    presence.xml = root
    return presence


def _make_presence_no_x(from_jid: str) -> MagicMock:
    """Build a mock presence stanza without MUC user extension."""
    presence = MagicMock()
    presence.get = MagicMock(side_effect=lambda key, default="": from_jid if key == "from" else default)
    root = Element("presence")
    root.set("from", from_jid)
    presence.xml = root
    return presence


# ---------------------------------------------------------------------------
# _extract_status_codes
# ---------------------------------------------------------------------------


class TestExtractStatusCodes:
    def test_single_code(self):
        p = _make_presence("room@muc.example.com/nick", [110])
        assert _extract_status_codes(p) == {110}

    def test_multiple_codes(self):
        p = _make_presence("room@muc.example.com/nick", [110, 210])
        assert _extract_status_codes(p) == {110, 210}

    def test_no_x_element(self):
        p = _make_presence_no_x("room@muc.example.com/nick")
        assert _extract_status_codes(p) == set()

    def test_empty_codes(self):
        p = _make_presence("room@muc.example.com/nick", [])
        assert _extract_status_codes(p) == set()

    def test_non_numeric_code_ignored(self):
        """Non-numeric code attributes are silently ignored."""
        p = _make_presence("room@muc.example.com/nick", [110])
        # Add a non-numeric status element manually
        x_elem = p.xml.find(f"{{{MUC_USER_NS}}}x")
        bad_status = SubElement(x_elem, f"{{{MUC_USER_NS}}}status")
        bad_status.set("code", "abc")
        assert _extract_status_codes(p) == {110}


# ---------------------------------------------------------------------------
# _extract_nick_from_presence / _extract_room_jid
# ---------------------------------------------------------------------------


class TestExtractJidParts:
    def test_nick_from_full_jid(self):
        p = _make_presence("room@muc.example.com/alice", [110])
        assert _extract_nick_from_presence(p) == "alice"

    def test_nick_from_bare_jid(self):
        p = _make_presence("room@muc.example.com", [110])
        assert _extract_nick_from_presence(p) == ""

    def test_room_jid_from_full_jid(self):
        p = _make_presence("room@muc.example.com/alice", [110])
        assert _extract_room_jid(p) == "room@muc.example.com"

    def test_room_jid_from_bare_jid(self):
        p = _make_presence("room@muc.example.com", [110])
        assert _extract_room_jid(p) == "room@muc.example.com"


# ---------------------------------------------------------------------------
# Status 110: Self-presence (Requirement 26.1)
# ---------------------------------------------------------------------------


class TestStatus110SelfPresence:
    def test_confirms_join(self):
        """Status 110 adds room to _confirmed_mucs."""
        comp = _make_comp()
        p = _make_presence("room@muc.example.com/bridge", [110])
        on_muc_presence(comp, p)
        assert "room@muc.example.com" in comp._confirmed_mucs

    def test_110_with_210_updates_nick(self):
        """Status 110+210 confirms join AND logs nick modification."""
        comp = _make_comp()
        p = _make_presence("room@muc.example.com/bridge_1", [110, 210])
        on_muc_presence(comp, p)
        assert "room@muc.example.com" in comp._confirmed_mucs


# ---------------------------------------------------------------------------
# Status 210: Nick modified (Requirement 26.2)
# ---------------------------------------------------------------------------


class TestStatus210NickModified:
    def test_nick_modified_logged(self):
        """Status 210 alone is handled without error."""
        comp = _make_comp()
        p = _make_presence("room@muc.example.com/alice_1", [210])
        # Should not raise
        on_muc_presence(comp, p)


# ---------------------------------------------------------------------------
# Status 301: Banned (Requirement 26.3)
# ---------------------------------------------------------------------------


class TestStatus301Banned:
    def test_adds_to_banned_rooms(self):
        comp = _make_comp()
        p = _make_presence("room@muc.example.com/bridge", [301])
        on_muc_presence(comp, p)
        assert "room@muc.example.com" in comp._banned_rooms

    def test_removes_puppet_entries(self):
        comp = _make_comp()
        comp._puppets_joined = {
            ("room@muc.example.com", "user1@bridge.example.com"),
            ("room@muc.example.com", "user2@bridge.example.com"),
            ("other@muc.example.com", "user1@bridge.example.com"),
        }
        p = _make_presence("room@muc.example.com/bridge", [301])
        on_muc_presence(comp, p)
        # Only the banned room's entries should be removed
        assert comp._puppets_joined == {("other@muc.example.com", "user1@bridge.example.com")}

    def test_removes_from_confirmed_mucs(self):
        comp = _make_comp()
        comp._confirmed_mucs.add("room@muc.example.com")
        p = _make_presence("room@muc.example.com/bridge", [301])
        on_muc_presence(comp, p)
        assert "room@muc.example.com" not in comp._confirmed_mucs

    def test_no_rejoin_scheduled(self):
        """Banned rooms must NOT trigger a rejoin, even with auto_rejoin enabled."""
        comp = _make_comp(auto_rejoin=True)
        p = _make_presence("room@muc.example.com/bridge", [301])
        with patch("bridge.adapters.xmpp.handlers.asyncio.ensure_future") as mock_ef:
            on_muc_presence(comp, p)
            mock_ef.assert_not_called()


# ---------------------------------------------------------------------------
# Status 307: Kicked (Requirement 26.4)
# ---------------------------------------------------------------------------


class TestStatus307Kicked:
    def test_removes_puppet_entries(self):
        comp = _make_comp()
        comp._puppets_joined = {("room@muc.example.com", "user@bridge.example.com")}
        p = _make_presence("room@muc.example.com/bridge", [307])
        with patch("bridge.adapters.xmpp.handlers.asyncio.ensure_future"):
            on_muc_presence(comp, p)
        assert ("room@muc.example.com", "user@bridge.example.com") not in comp._puppets_joined

    def test_removes_from_confirmed_mucs(self):
        comp = _make_comp()
        comp._confirmed_mucs.add("room@muc.example.com")
        p = _make_presence("room@muc.example.com/bridge", [307])
        with patch("bridge.adapters.xmpp.handlers.asyncio.ensure_future"):
            on_muc_presence(comp, p)
        assert "room@muc.example.com" not in comp._confirmed_mucs

    def test_schedules_rejoin_when_auto_rejoin_enabled(self):
        comp = _make_comp(auto_rejoin=True)
        p = _make_presence("room@muc.example.com/bridge", [307])
        with patch("bridge.adapters.xmpp.handlers.asyncio.ensure_future") as mock_ef:
            on_muc_presence(comp, p)
            mock_ef.assert_called_once()

    def test_no_rejoin_when_auto_rejoin_disabled(self):
        comp = _make_comp(auto_rejoin=False)
        p = _make_presence("room@muc.example.com/bridge", [307])
        with patch("bridge.adapters.xmpp.handlers.asyncio.ensure_future") as mock_ef:
            on_muc_presence(comp, p)
            mock_ef.assert_not_called()


# ---------------------------------------------------------------------------
# Status 321/322/332: Removal / shutdown (Requirement 26.5)
# ---------------------------------------------------------------------------


class TestStatus321AffiliationChange:
    def test_removes_puppet_entries(self):
        comp = _make_comp()
        comp._puppets_joined = {("room@muc.example.com", "user@bridge.example.com")}
        p = _make_presence("room@muc.example.com/bridge", [321])
        with patch("bridge.adapters.xmpp.handlers.asyncio.ensure_future"):
            on_muc_presence(comp, p)
        assert ("room@muc.example.com", "user@bridge.example.com") not in comp._puppets_joined

    def test_schedules_rejoin_when_auto_rejoin_enabled(self):
        comp = _make_comp(auto_rejoin=True)
        p = _make_presence("room@muc.example.com/bridge", [321])
        with patch("bridge.adapters.xmpp.handlers.asyncio.ensure_future") as mock_ef:
            on_muc_presence(comp, p)
            mock_ef.assert_called_once()


class TestStatus322MembersOnly:
    def test_removes_puppet_entries(self):
        comp = _make_comp()
        comp._puppets_joined = {("room@muc.example.com", "user@bridge.example.com")}
        p = _make_presence("room@muc.example.com/bridge", [322])
        with patch("bridge.adapters.xmpp.handlers.asyncio.ensure_future"):
            on_muc_presence(comp, p)
        assert ("room@muc.example.com", "user@bridge.example.com") not in comp._puppets_joined

    def test_schedules_rejoin_when_auto_rejoin_enabled(self):
        comp = _make_comp(auto_rejoin=True)
        p = _make_presence("room@muc.example.com/bridge", [322])
        with patch("bridge.adapters.xmpp.handlers.asyncio.ensure_future") as mock_ef:
            on_muc_presence(comp, p)
            mock_ef.assert_called_once()


class TestStatus332ServerShutdown:
    def test_removes_puppet_entries(self):
        comp = _make_comp()
        comp._puppets_joined = {("room@muc.example.com", "user@bridge.example.com")}
        p = _make_presence("room@muc.example.com/bridge", [332])
        on_muc_presence(comp, p)
        assert ("room@muc.example.com", "user@bridge.example.com") not in comp._puppets_joined

    def test_no_rejoin_on_shutdown(self):
        """Status 332 (server shutdown) should NOT trigger rejoin."""
        comp = _make_comp(auto_rejoin=True)
        p = _make_presence("room@muc.example.com/bridge", [332])
        with patch("bridge.adapters.xmpp.handlers.asyncio.ensure_future") as mock_ef:
            on_muc_presence(comp, p)
            mock_ef.assert_not_called()

    def test_removes_from_confirmed_mucs(self):
        comp = _make_comp()
        comp._confirmed_mucs.add("room@muc.example.com")
        p = _make_presence("room@muc.example.com/bridge", [332])
        on_muc_presence(comp, p)
        assert "room@muc.example.com" not in comp._confirmed_mucs


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_no_status_codes_is_noop(self):
        """Presence without status codes should be a no-op."""
        comp = _make_comp()
        p = _make_presence_no_x("room@muc.example.com/alice")
        on_muc_presence(comp, p)
        assert comp._confirmed_mucs == set()
        assert comp._banned_rooms == set()

    def test_empty_status_codes_is_noop(self):
        """Presence with x element but no status codes should be a no-op."""
        comp = _make_comp()
        p = _make_presence("room@muc.example.com/alice", [])
        on_muc_presence(comp, p)
        assert comp._confirmed_mucs == set()

    def test_remove_puppet_entries_only_affects_target_room(self):
        """_remove_puppet_entries only removes entries for the specified room."""
        comp = _make_comp()
        comp._puppets_joined = {
            ("room1@muc.example.com", "user@bridge.example.com"),
            ("room2@muc.example.com", "user@bridge.example.com"),
        }
        _remove_puppet_entries(comp, "room1@muc.example.com")
        assert comp._puppets_joined == {("room2@muc.example.com", "user@bridge.example.com")}

    def test_banned_room_prevents_rejoin(self):
        """If a room is in _banned_rooms, _rejoin_muc should skip it."""
        comp = _make_comp()
        comp._banned_rooms.add("room@muc.example.com")
        from bridge.adapters.xmpp.handlers import _rejoin_muc

        loop = asyncio.new_event_loop()
        try:
            with patch("bridge.adapters.xmpp.handlers.asyncio.sleep", new_callable=AsyncMock):
                loop.run_until_complete(_rejoin_muc(comp, "room@muc.example.com"))
        finally:
            loop.close()
        # join_muc_wait should NOT have been called
        comp.plugin["xep_0045"].join_muc_wait.assert_not_called()
