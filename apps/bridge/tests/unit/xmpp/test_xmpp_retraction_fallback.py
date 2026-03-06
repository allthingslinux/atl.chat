"""Tests for XMPP retraction fallback elements (Requirements 25.1, 25.2).

Verifies that retraction stanzas include:
- <body> with fallback text for non-supporting clients
- <fallback xmlns="urn:xmpp:fallback:0" for="urn:xmpp:message-retract:1"/>
- <store xmlns="urn:xmpp:hints"/> hint for archival
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from bridge.adapters.xmpp.component import XMPPComponent
from bridge.adapters.xmpp.msgid import XMPPMessageIDTracker
from bridge.adapters.xmpp.outbound import (
    RETRACTION_FALLBACK_BODY,
    send_retraction_as_bridge,
    send_retraction_as_user,
)
from cachetools import TTLCache

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_component() -> Any:
    """Instantiate XMPPComponent bypassing slixmpp __init__."""
    comp: Any = object.__new__(XMPPComponent)
    comp._bus = MagicMock()
    comp._router = MagicMock()
    comp._identity = MagicMock()
    comp._component_jid = "bridge.example.com"
    comp._session = None
    comp._avatar_cache = TTLCache(maxsize=100, ttl=86400)
    comp._ibb_streams = {}
    comp._msgid_tracker = XMPPMessageIDTracker()
    comp._puppets_joined = set()
    comp._avatar_broadcast_done = set()
    comp._recent_sent_nicks = TTLCache(maxsize=200, ttl=10)
    comp.plugin = MagicMock()
    comp._run_out_filters = None
    return comp


def _mock_jid_escape_plugin(escaped: str = "escapednick") -> MagicMock:
    plugin = MagicMock()
    plugin.escape.return_value = escaped
    return plugin


def _make_plugin_registry(**plugins: Any) -> MagicMock:
    registry = MagicMock()
    registry.get.side_effect = lambda name, default=None: plugins.get(name, default)
    return registry


class _StanzaRecorder:
    """Lightweight fake message that records element operations."""

    def __init__(self) -> None:
        self.body: str | None = None
        self._enabled: dict[str, Any] = {}
        self._items: dict[str, Any] = {}
        self.sent = False

    def enable(self, name: str) -> _StanzaRecorder:
        sub = _StanzaRecorder()
        self._enabled[name] = sub
        return sub

    def __setitem__(self, key: str, value: Any) -> None:
        self._items[key] = value

    def __getitem__(self, key: str) -> Any:
        if key not in self._items:
            self._items[key] = {}
        return self._items[key]

    def send(self) -> None:
        self.sent = True


# ---------------------------------------------------------------------------
# send_retraction_as_user
# ---------------------------------------------------------------------------


class TestSendRetractionAsUserFallback:
    """Validates: Requirements 25.1, 25.2"""

    @pytest.mark.asyncio
    async def test_retraction_includes_fallback_body(self):
        """The retraction stanza must include a <body> with fallback text."""
        comp = _make_component()
        recorder = _StanzaRecorder()
        comp.make_message = MagicMock(return_value=recorder)
        comp.plugin = _make_plugin_registry(xep_0106=_mock_jid_escape_plugin())

        await send_retraction_as_user(comp, "d1", "room@conf.example.com", "msg-1", "Nick")

        # body is passed as mbody kwarg to make_message
        call_kwargs = comp.make_message.call_args[1]
        assert call_kwargs["mbody"] == RETRACTION_FALLBACK_BODY

    @pytest.mark.asyncio
    async def test_retraction_includes_fallback_element_with_for_attribute(self):
        """The retraction stanza must include <fallback for="urn:xmpp:message-retract:1"/>."""
        comp = _make_component()
        recorder = _StanzaRecorder()
        comp.make_message = MagicMock(return_value=recorder)
        comp.plugin = _make_plugin_registry(xep_0106=_mock_jid_escape_plugin())

        await send_retraction_as_user(comp, "d1", "room@conf.example.com", "msg-1", "Nick")

        assert "fallback" in recorder._enabled
        fb = recorder._enabled["fallback"]
        assert fb._items.get("for") == "urn:xmpp:message-retract:1"

    @pytest.mark.asyncio
    async def test_retraction_includes_store_hint(self):
        """The retraction stanza must include <store xmlns="urn:xmpp:hints"/>."""
        comp = _make_component()
        recorder = _StanzaRecorder()
        comp.make_message = MagicMock(return_value=recorder)
        comp.plugin = _make_plugin_registry(xep_0106=_mock_jid_escape_plugin())

        await send_retraction_as_user(comp, "d1", "room@conf.example.com", "msg-1", "Nick")

        assert "store" in recorder._enabled

    @pytest.mark.asyncio
    async def test_retraction_includes_retract_element(self):
        """The retraction stanza must include <retract id="target_msg_id"/>."""
        comp = _make_component()
        recorder = _StanzaRecorder()
        comp.make_message = MagicMock(return_value=recorder)
        comp.plugin = _make_plugin_registry(xep_0106=_mock_jid_escape_plugin())

        await send_retraction_as_user(comp, "d1", "room@conf.example.com", "msg-1", "Nick")

        retract = recorder._items.get("retract", {})
        assert retract.get("id") == "msg-1"

    @pytest.mark.asyncio
    async def test_retraction_stanza_is_sent(self):
        """The retraction stanza must actually be sent."""
        comp = _make_component()
        recorder = _StanzaRecorder()
        comp.make_message = MagicMock(return_value=recorder)
        comp.plugin = _make_plugin_registry(xep_0106=_mock_jid_escape_plugin())

        await send_retraction_as_user(comp, "d1", "room@conf.example.com", "msg-1", "Nick")

        assert recorder.sent is True


# ---------------------------------------------------------------------------
# send_retraction_as_bridge
# ---------------------------------------------------------------------------


class TestSendRetractionAsBridgeFallback:
    """Validates: Requirements 25.1, 25.2"""

    @pytest.mark.asyncio
    async def test_bridge_retraction_includes_fallback_body(self):
        """Bridge retraction stanza must include a <body> with fallback text."""
        comp = _make_component()
        recorder = _StanzaRecorder()
        comp.make_message = MagicMock(return_value=recorder)

        await send_retraction_as_bridge(comp, "room@conf.example.com", "msg-1")

        call_kwargs = comp.make_message.call_args[1]
        assert call_kwargs["mbody"] == RETRACTION_FALLBACK_BODY

    @pytest.mark.asyncio
    async def test_bridge_retraction_includes_fallback_element_with_for_attribute(self):
        """Bridge retraction stanza must include <fallback for="urn:xmpp:message-retract:1"/>."""
        comp = _make_component()
        recorder = _StanzaRecorder()
        comp.make_message = MagicMock(return_value=recorder)

        await send_retraction_as_bridge(comp, "room@conf.example.com", "msg-1")

        assert "fallback" in recorder._enabled
        fb = recorder._enabled["fallback"]
        assert fb._items.get("for") == "urn:xmpp:message-retract:1"

    @pytest.mark.asyncio
    async def test_bridge_retraction_includes_store_hint(self):
        """Bridge retraction stanza must include <store xmlns="urn:xmpp:hints"/>."""
        comp = _make_component()
        recorder = _StanzaRecorder()
        comp.make_message = MagicMock(return_value=recorder)

        await send_retraction_as_bridge(comp, "room@conf.example.com", "msg-1")

        assert "store" in recorder._enabled

    @pytest.mark.asyncio
    async def test_bridge_retraction_includes_retract_element(self):
        """Bridge retraction stanza must include <retract id="target_msg_id"/>."""
        comp = _make_component()
        recorder = _StanzaRecorder()
        comp.make_message = MagicMock(return_value=recorder)

        await send_retraction_as_bridge(comp, "room@conf.example.com", "msg-1")

        retract = recorder._items.get("retract", {})
        assert retract.get("id") == "msg-1"

    @pytest.mark.asyncio
    async def test_bridge_retraction_uses_bridge_jid(self):
        """Bridge retraction must use bridge@component_jid as mfrom."""
        comp = _make_component()
        recorder = _StanzaRecorder()
        comp.make_message = MagicMock(return_value=recorder)

        await send_retraction_as_bridge(comp, "room@conf.example.com", "msg-1")

        call_kwargs = comp.make_message.call_args[1]
        assert str(call_kwargs["mfrom"]) == "bridge@bridge.example.com"

    @pytest.mark.asyncio
    async def test_bridge_retraction_exception_is_swallowed(self):
        """Exceptions during bridge retraction must not propagate."""
        comp = _make_component()
        mock_msg = MagicMock()
        mock_msg.send.side_effect = RuntimeError("err")
        comp.make_message = MagicMock(return_value=mock_msg)

        # Must not raise
        await send_retraction_as_bridge(comp, "room@conf.example.com", "msg-1")
