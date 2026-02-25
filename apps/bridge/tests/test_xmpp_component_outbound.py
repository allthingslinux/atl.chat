"""Tests for XMPPComponent outbound send methods and lifecycle handlers."""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bridge.adapters.xmpp_component import XMPPComponent, _escape_jid_node
from bridge.adapters.xmpp_msgid import XMPPMessageIDTracker
from cachetools import TTLCache

pytestmark = pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")


# ---------------------------------------------------------------------------
# _escape_jid_node (XEP-0106)
# ---------------------------------------------------------------------------


class TestEscapeJidNode:
    """XEP-0106 JID node escaping."""

    def test_passes_through_safe_chars(self):
        assert _escape_jid_node("Nick") == "Nick"
        assert _escape_jid_node("1046905234200469504") == "1046905234200469504"

    def test_escapes_disallowed_chars(self):
        assert _escape_jid_node("a b") == "a\\20b"
        assert _escape_jid_node("user@host") == "user\\40host"
        assert _escape_jid_node("a\\b") == "a\\5cb"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_component(router=None, bus=None) -> Any:
    """Instantiate XMPPComponent bypassing slixmpp __init__.

    Returns Any so the type checker allows mock-attribute access.
    """
    comp: Any = object.__new__(XMPPComponent)
    comp._bus = bus or MagicMock()
    comp._router = router or MagicMock()
    comp._identity = MagicMock()
    comp._component_jid = "bridge.example.com"
    comp._session = None
    comp._avatar_cache = TTLCache(maxsize=100, ttl=86400)
    comp._ibb_streams = {}
    comp._msgid_tracker = XMPPMessageIDTracker()
    comp._puppets_joined = set()
    # Mock plugin() lookup and message creation
    comp.plugin = MagicMock()
    comp.make_message = MagicMock()
    # Router.all_mappings() returns [] so _on_session_start MUC join loop is empty
    if isinstance(comp._router, MagicMock):
        comp._router.all_mappings.return_value = []
    return comp


def _mock_jid_escape_plugin(escaped="escapednick"):
    plugin = MagicMock()
    plugin.escape.return_value = escaped
    return plugin


def _make_plugin_registry(**plugins):
    """Return a plugin MagicMock where plugin.get(name) returns the given mock (or None)."""
    registry = MagicMock()
    registry.get.side_effect = lambda name, default=None: plugins.get(name, default)
    return registry


# ---------------------------------------------------------------------------
# _on_session_start / _on_disconnected
# ---------------------------------------------------------------------------


class TestSessionLifecycle:
    @pytest.mark.asyncio
    async def test_on_session_start_creates_session_when_none(self):
        # Arrange
        comp = make_component()
        comp._session = None

        # Act
        with patch("aiohttp.ClientSession") as mock_session_cls:
            await comp._on_session_start(None)

        # Assert
        mock_session_cls.assert_called_once()
        assert comp._session is not None

    @pytest.mark.asyncio
    async def test_on_session_start_does_not_replace_existing_session(self):
        # Arrange
        comp = make_component()
        existing = MagicMock()
        comp._session = existing

        # Act
        with patch("aiohttp.ClientSession") as mock_session_cls:
            await comp._on_session_start(None)

        # Assert
        mock_session_cls.assert_not_called()
        assert comp._session is existing

    @pytest.mark.asyncio
    async def test_on_disconnected_closes_session(self):
        # Arrange
        comp = make_component()
        mock_session = AsyncMock()
        comp._session = mock_session

        # Act
        await comp._on_disconnected(None)

        # Assert
        mock_session.close.assert_awaited_once()
        assert comp._session is None

    @pytest.mark.asyncio
    async def test_on_disconnected_no_session_is_safe(self):
        # Arrange
        comp = make_component()
        comp._session = None

        # Act / Assert — must not raise
        await comp._on_disconnected(None)


# ---------------------------------------------------------------------------
# send_message_as_user
# ---------------------------------------------------------------------------


class TestSendMessageAsUser:
    @pytest.mark.asyncio
    async def test_sends_message_and_returns_id(self):
        # Arrange
        comp = make_component()
        mock_msg = MagicMock()
        mock_msg.__getitem__ = MagicMock(return_value="generated-uuid")
        comp.make_message.return_value = mock_msg
        comp.plugin = _make_plugin_registry(xep_0106=_mock_jid_escape_plugin("escapednick"))

        # Act
        result = await comp.send_message_as_user("d1", "room@conf.example.com", "hello", "Nick")

        # Assert
        comp.make_message.assert_called_once()
        mock_msg.send.assert_called_once()
        assert result == "generated-uuid"

    @pytest.mark.asyncio
    async def test_spoiler_content_stripped_and_enabled(self):
        # Arrange
        comp = make_component()
        mock_msg = MagicMock()
        mock_msg.__getitem__ = MagicMock(return_value="msg-id")
        comp.make_message.return_value = mock_msg
        comp.plugin = _make_plugin_registry(xep_0106=_mock_jid_escape_plugin())

        # Act
        await comp.send_message_as_user("d1", "room@conf.example.com", "||secret||", "Nick")

        # Assert — body sent to make_message has spoiler markers stripped
        call_kwargs = comp.make_message.call_args[1]
        assert "||" not in call_kwargs["mbody"]
        mock_msg.enable.assert_any_call("spoiler")

    @pytest.mark.asyncio
    async def test_with_explicit_msg_id(self):
        # Arrange
        comp = make_component()
        mock_msg = MagicMock()
        mock_msg.__getitem__ = MagicMock(return_value="explicit-id")
        comp.make_message.return_value = mock_msg
        comp.plugin = _make_plugin_registry(xep_0106=_mock_jid_escape_plugin())

        # Act
        await comp.send_message_as_user("d1", "room@conf.example.com", "hello", "Nick", xmpp_msg_id="explicit-id")

        # Assert — the explicit id was set on the message stanza
        mock_msg.__setitem__.assert_any_call("id", "explicit-id")

    @pytest.mark.asyncio
    async def test_exception_during_send_returns_empty(self):
        # Arrange
        comp = make_component()
        mock_msg = MagicMock()
        mock_msg.send.side_effect = RuntimeError("XMPP error")
        comp.make_message.return_value = mock_msg
        comp.plugin = _make_plugin_registry(xep_0106=_mock_jid_escape_plugin())

        # Act
        result = await comp.send_message_as_user("d1", "room@conf.example.com", "hello", "Nick")

        # Assert
        assert result == ""


# ---------------------------------------------------------------------------
# send_reaction_as_user
# ---------------------------------------------------------------------------


class TestSendReactionAsUser:
    @pytest.mark.asyncio
    async def test_no_jid_escape_plugin_returns_early(self):
        # Arrange
        comp = make_component()
        comp.plugin = _make_plugin_registry()

        # Act / Assert — must not raise
        await comp.send_reaction_as_user("d1", "room@conf.example.com", "msg-1", "👍", "Nick")

    @pytest.mark.asyncio
    async def test_no_reactions_plugin_returns_early(self):
        # Arrange — escape plugin present but reactions plugin absent
        comp = make_component()
        comp.plugin = _make_plugin_registry(xep_0106=_mock_jid_escape_plugin())

        # Act / Assert — must not raise
        await comp.send_reaction_as_user("d1", "room@conf.example.com", "msg-1", "👍", "Nick")

    @pytest.mark.asyncio
    async def test_sends_reaction_via_plugin(self):
        # Arrange
        comp = make_component()
        reactions_plugin = MagicMock()
        reactions_plugin.set_reactions = MagicMock()
        mock_msg = MagicMock()
        comp.make_message.return_value = mock_msg
        comp.plugin = _make_plugin_registry(
            xep_0106=_mock_jid_escape_plugin(),
            xep_0444=reactions_plugin,
        )

        # Act
        await comp.send_reaction_as_user("d1", "room@conf.example.com", "msg-1", "👍", "Nick")

        # Assert — we use set_reactions + make_message (send_reactions has no ifrom for components)
        reactions_plugin.set_reactions.assert_called_once()
        mock_msg.enable.assert_called_once_with("store")
        mock_msg.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_exception_during_reaction_send_is_swallowed(self):
        # Arrange
        comp = make_component()
        reactions_plugin = MagicMock()
        reactions_plugin.set_reactions.side_effect = RuntimeError("network error")
        comp.make_message.return_value = MagicMock()
        comp.plugin = _make_plugin_registry(
            xep_0106=_mock_jid_escape_plugin(),
            xep_0444=reactions_plugin,
        )

        # Act / Assert — must not raise
        await comp.send_reaction_as_user("d1", "room@conf.example.com", "msg-1", "👍", "Nick")


# ---------------------------------------------------------------------------
# send_retraction_as_user
# ---------------------------------------------------------------------------


class TestSendRetractionAsUser:
    @pytest.mark.asyncio
    async def test_no_jid_escape_plugin_returns_early(self):
        # Arrange
        comp = make_component()
        comp.plugin = _make_plugin_registry()

        # Act / Assert — must not raise
        await comp.send_retraction_as_user("d1", "room@conf.example.com", "msg-1", "Nick")

    @pytest.mark.asyncio
    async def test_no_retraction_plugin_returns_early(self):
        # Arrange
        comp = make_component()
        comp.plugin = _make_plugin_registry(xep_0106=_mock_jid_escape_plugin())

        # Act / Assert — must not raise
        await comp.send_retraction_as_user("d1", "room@conf.example.com", "msg-1", "Nick")

    @pytest.mark.asyncio
    async def test_sends_retraction_via_plugin(self):
        # Arrange
        comp = make_component()
        retract_plugin = AsyncMock()
        comp.plugin = _make_plugin_registry(
            xep_0106=_mock_jid_escape_plugin(),
            xep_0424=retract_plugin,
        )

        # Act
        await comp.send_retraction_as_user("d1", "room@conf.example.com", "msg-1", "Nick")

        # Assert
        retract_plugin.send_retraction.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_exception_during_retraction_send_is_swallowed(self):
        # Arrange
        comp = make_component()
        retract_plugin = AsyncMock()
        retract_plugin.send_retraction.side_effect = RuntimeError("err")
        comp.plugin = _make_plugin_registry(
            xep_0106=_mock_jid_escape_plugin(),
            xep_0424=retract_plugin,
        )

        # Act / Assert — must not raise
        await comp.send_retraction_as_user("d1", "room@conf.example.com", "msg-1", "Nick")


# ---------------------------------------------------------------------------
# send_correction_as_user
# ---------------------------------------------------------------------------


class TestSendCorrectionAsUser:
    @pytest.mark.asyncio
    async def test_sends_correction_with_replace_id(self):
        # Arrange
        comp = make_component()
        mock_msg = MagicMock()
        comp.make_message.return_value = mock_msg
        comp.plugin = _make_plugin_registry(xep_0106=_mock_jid_escape_plugin())

        # Act
        await comp.send_correction_as_user("d1", "room@conf.example.com", "corrected text", "Nick", "orig-1")

        # Assert
        comp.make_message.assert_called_once()
        mock_msg.__getitem__.assert_called_with("replace")
        mock_msg.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_exception_during_correction_is_swallowed(self):
        # Arrange
        comp = make_component()
        mock_msg = MagicMock()
        mock_msg.send.side_effect = RuntimeError("err")
        comp.make_message.return_value = mock_msg
        comp.plugin = _make_plugin_registry(xep_0106=_mock_jid_escape_plugin())

        # Act / Assert — must not raise
        await comp.send_correction_as_user("d1", "room@conf.example.com", "text", "Nick", "orig-1")


# ---------------------------------------------------------------------------
# join_muc_as_user
# ---------------------------------------------------------------------------


class TestJoinMucAsUser:
    @pytest.mark.asyncio
    async def test_no_jid_escape_plugin_returns_early(self):
        # Arrange
        comp = make_component()
        comp.plugin = _make_plugin_registry()

        # Act / Assert — must not raise
        await comp.join_muc_as_user("room@conf.example.com", "Nick")

    @pytest.mark.asyncio
    async def test_no_muc_plugin_returns_early(self):
        # Arrange
        comp = make_component()
        comp.plugin = _make_plugin_registry(xep_0106=_mock_jid_escape_plugin())

        # Act / Assert — must not raise
        await comp.join_muc_as_user("room@conf.example.com", "Nick")

    @pytest.mark.asyncio
    async def test_joins_muc_with_plugin(self):
        # Arrange
        comp = make_component()
        muc_plugin = AsyncMock()
        comp.plugin = _make_plugin_registry(
            xep_0106=_mock_jid_escape_plugin(),
            xep_0045=muc_plugin,
        )

        # Act
        await comp.join_muc_as_user("room@conf.example.com", "Nick")

        # Assert
        muc_plugin.join_muc_wait.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_xmpp_error_during_join_is_logged_not_raised(self):
        # Arrange
        from slixmpp.exceptions import XMPPError

        comp = make_component()
        muc_plugin = AsyncMock()
        muc_plugin.join_muc_wait.side_effect = XMPPError("service-unavailable")
        comp.plugin = _make_plugin_registry(
            xep_0106=_mock_jid_escape_plugin(),
            xep_0045=muc_plugin,
        )

        # Act / Assert — must not raise
        await comp.join_muc_as_user("room@conf.example.com", "Nick")


# ---------------------------------------------------------------------------
# _fetch_avatar_bytes
# ---------------------------------------------------------------------------


class TestFetchAvatarBytes:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_session(self):
        # Arrange
        comp = make_component()
        comp._session = None

        # Act
        result = await comp._fetch_avatar_bytes("https://cdn.example.com/avatar.png")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_bytes_on_200(self):
        # Arrange
        comp = make_component()
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=b"image_data")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        comp._session = mock_session

        # Act
        result = await comp._fetch_avatar_bytes("https://cdn.example.com/avatar.png")

        # Assert
        assert result == b"image_data"

    @pytest.mark.asyncio
    async def test_returns_none_on_non_200(self):
        # Arrange
        comp = make_component()
        mock_resp = AsyncMock()
        mock_resp.status = 404
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        comp._session = mock_session

        # Act
        result = await comp._fetch_avatar_bytes("https://cdn.example.com/avatar.png")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        # Arrange
        comp = make_component()
        mock_session = MagicMock()
        mock_session.get.side_effect = OSError("connection refused")
        comp._session = mock_session

        # Act
        result = await comp._fetch_avatar_bytes("https://cdn.example.com/avatar.png")

        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# set_avatar_for_user
# ---------------------------------------------------------------------------


class TestSetAvatarForUser:
    @pytest.mark.asyncio
    async def test_skips_when_no_avatar_url(self):
        # Arrange
        comp = make_component()
        comp.plugin = _make_plugin_registry()

        # Act
        await comp.set_avatar_for_user("d1", "Nick", None)

        # Assert — plugin was never consulted
        comp.plugin.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_no_jid_escape_plugin(self):
        # Arrange — no escape plugin, but a URL is provided
        comp = make_component()
        comp.plugin = _make_plugin_registry()
        comp._fetch_avatar_bytes = AsyncMock(return_value=b"img")

        # Act / Assert — must not raise
        await comp.set_avatar_for_user("d1", "Nick", "https://cdn.example.com/avatar.png")

    @pytest.mark.asyncio
    async def test_skips_when_fetch_returns_none(self):
        # Arrange — fetch returns None (e.g. HTTP error)
        comp = make_component()
        comp.plugin = _make_plugin_registry(xep_0106=_mock_jid_escape_plugin())
        comp._fetch_avatar_bytes = AsyncMock(return_value=None)

        # Act / Assert — no vcard ops should happen
        await comp.set_avatar_for_user("d1", "Nick", "https://cdn.example.com/avatar.png")

    @pytest.mark.asyncio
    async def test_skips_when_avatar_hash_unchanged(self):
        # Arrange — same hash is already in the cache
        comp = make_component()
        img_bytes = b"image_data"
        img_hash = hashlib.sha1(img_bytes).hexdigest()
        comp._avatar_cache["d1"] = img_hash
        comp._fetch_avatar_bytes = AsyncMock(return_value=img_bytes)
        vcard_plugin = AsyncMock()
        comp.plugin = _make_plugin_registry(
            xep_0106=_mock_jid_escape_plugin(),
            xep_0054=vcard_plugin,
        )

        # Act
        await comp.set_avatar_for_user("d1", "Nick", "https://cdn.example.com/avatar.png")

        # Assert — vcard was not re-published because the hash is unchanged
        vcard_plugin.publish_vcard.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_publishes_vcard_when_avatar_changed(self):
        # Arrange — new image, cache miss
        comp = make_component()
        img_bytes = b"new_image_data"
        comp._fetch_avatar_bytes = AsyncMock(return_value=img_bytes)
        vcard_obj = MagicMock()
        vcard_plugin = MagicMock()
        vcard_plugin.make_vcard.return_value = vcard_obj
        vcard_plugin.publish_vcard = AsyncMock()
        comp.plugin = _make_plugin_registry(
            xep_0106=_mock_jid_escape_plugin("nick"),
            xep_0054=vcard_plugin,
        )

        # Act
        await comp.set_avatar_for_user("d1", "Nick", "https://cdn.example.com/avatar.png")

        # Assert — vcard published and avatar hash cached
        vcard_plugin.publish_vcard.assert_awaited_once()
        expected_hash = hashlib.sha1(img_bytes).hexdigest()
        assert comp._avatar_cache.get("d1") == expected_hash

    @pytest.mark.asyncio
    async def test_skips_when_no_vcard_plugin(self):
        # Arrange — xep_0054 missing from plugin registry
        comp = make_component()
        img_bytes = b"image"
        comp._fetch_avatar_bytes = AsyncMock(return_value=img_bytes)
        comp.plugin = _make_plugin_registry(xep_0106=_mock_jid_escape_plugin())

        # Act / Assert — must not raise
        await comp.set_avatar_for_user("d1", "Nick", "https://cdn.example.com/avatar.png")

    @pytest.mark.asyncio
    async def test_exception_during_vcard_publish_is_swallowed(self):
        # Arrange
        comp = make_component()
        img_bytes = b"image"
        comp._fetch_avatar_bytes = AsyncMock(return_value=img_bytes)
        vcard_obj = MagicMock()
        vcard_plugin = MagicMock()
        vcard_plugin.make_vcard.return_value = vcard_obj
        vcard_plugin.publish_vcard = AsyncMock(side_effect=RuntimeError("vcard error"))
        comp.plugin = _make_plugin_registry(
            xep_0106=_mock_jid_escape_plugin(),
            xep_0054=vcard_plugin,
        )

        # Act / Assert — must not raise
        await comp.set_avatar_for_user("d1", "Nick", "https://cdn.example.com/avatar.png")


# ---------------------------------------------------------------------------
# IBB stream handlers
# ---------------------------------------------------------------------------


class TestIbbStreamHandlers:
    def test_on_ibb_stream_start_stores_task(self):
        # Arrange
        comp = make_component()
        stream = MagicMock()
        stream.sid = "sid-1234"
        stream.peer = "room@conf.example.com/nick"
        stream.block_size = 4096

        async def _fake_handle(s):
            await asyncio.sleep(9999)

        # Act
        with (
            patch.object(comp, "_handle_ibb_stream", side_effect=_fake_handle),
            patch("asyncio.create_task", return_value=MagicMock()) as mock_task,
        ):
            comp._on_ibb_stream_start(stream)

        # Assert
        mock_task.assert_called_once()
        assert "sid-1234" in comp._ibb_streams

    def test_on_ibb_stream_end_cancels_task(self):
        # Arrange
        comp = make_component()
        mock_task = MagicMock()
        comp._ibb_streams["sid-abc"] = mock_task
        stream = MagicMock()
        stream.sid = "sid-abc"

        # Act
        comp._on_ibb_stream_end(stream)

        # Assert
        mock_task.cancel.assert_called_once()
        assert "sid-abc" not in comp._ibb_streams

    def test_on_ibb_stream_end_unknown_sid_is_safe(self):
        # Arrange
        comp = make_component()
        stream = MagicMock()
        stream.sid = "unknown-sid"

        # Act / Assert — must not raise
        comp._on_ibb_stream_end(stream)

    @pytest.mark.asyncio
    async def test_handle_ibb_stream_timeout_is_logged(self):
        # Arrange
        comp = make_component()
        stream = AsyncMock()
        stream.sid = "sid-timeout"
        stream.gather.side_effect = asyncio.TimeoutError()

        # Act / Assert — must not raise
        await comp._handle_ibb_stream(stream)

    @pytest.mark.asyncio
    async def test_handle_ibb_stream_exception_is_logged(self):
        # Arrange
        comp = make_component()
        stream = AsyncMock()
        stream.sid = "sid-err"
        stream.gather.side_effect = RuntimeError("read error")

        # Act / Assert — must not raise
        await comp._handle_ibb_stream(stream)

    @pytest.mark.asyncio
    async def test_handle_ibb_stream_success_removes_from_dict(self):
        # Arrange
        comp = make_component()
        stream = AsyncMock()
        stream.sid = "sid-ok"
        stream.peer = "room@conf.example.com/nick"
        stream.gather = AsyncMock(return_value=b"file_content")
        comp._ibb_streams["sid-ok"] = MagicMock()
        comp._router.get_mapping_for_xmpp.return_value = None  # bails early after gather

        # Act
        await comp._handle_ibb_stream(stream)

        # Assert
        assert "sid-ok" not in comp._ibb_streams


# ---------------------------------------------------------------------------
# send_file_with_fallback
# ---------------------------------------------------------------------------


class TestSendFileWithFallback:
    @pytest.mark.asyncio
    async def test_uses_http_when_available(self):
        # Arrange
        comp = make_component()
        comp.send_file_url_as_user = AsyncMock()
        comp.send_file_as_user = AsyncMock()

        # Act
        await comp.send_file_with_fallback("d1", "room@conf.example.com", b"data", "file.txt", "Nick")

        # Assert — HTTP upload path taken; IBB path not reached
        comp.send_file_url_as_user.assert_awaited_once()
        comp.send_file_as_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_falls_back_to_ibb_on_http_failure(self):
        # Arrange — HTTP upload raises, so IBB should be the fallback
        comp = make_component()
        comp.send_file_url_as_user = AsyncMock(side_effect=RuntimeError("HTTP failed"))
        comp.send_file_as_user = AsyncMock()

        # Act
        await comp.send_file_with_fallback("d1", "room@conf.example.com", b"data", "file.txt", "Nick")

        # Assert
        comp.send_file_as_user.assert_awaited_once()


# ---------------------------------------------------------------------------
# send_file_as_user
# ---------------------------------------------------------------------------


class TestSendFileAsUser:
    @pytest.mark.asyncio
    async def test_no_jid_escape_plugin_returns_early(self):
        # Arrange
        comp = make_component()
        comp.plugin = _make_plugin_registry()

        # Act / Assert — must not raise
        await comp.send_file_as_user("d1", "peer@example.com", b"data", "Nick")

    @pytest.mark.asyncio
    async def test_no_ibb_plugin_returns_early(self):
        # Arrange — escape plugin present but IBB plugin absent
        comp = make_component()
        comp.plugin = _make_plugin_registry(xep_0106=_mock_jid_escape_plugin())

        # Act / Assert — must not raise
        await comp.send_file_as_user("d1", "peer@example.com", b"data", "Nick")

    @pytest.mark.asyncio
    async def test_sends_file_via_ibb(self):
        # Arrange
        comp = make_component()
        ibb_plugin = AsyncMock()
        mock_stream = AsyncMock()
        ibb_plugin.open_stream.return_value = mock_stream
        comp.plugin = _make_plugin_registry(
            xep_0106=_mock_jid_escape_plugin(),
            xep_0047=ibb_plugin,
        )

        # Act
        await comp.send_file_as_user("d1", "peer@example.com", b"data", "Nick")

        # Assert
        ibb_plugin.open_stream.assert_awaited_once()
        mock_stream.sendall.assert_awaited_once_with(b"data")
        mock_stream.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_exception_during_ibb_send_is_swallowed(self):
        # Arrange — IBB open_stream itself raises
        comp = make_component()
        ibb_plugin = AsyncMock()
        ibb_plugin.open_stream.side_effect = RuntimeError("ibb error")
        comp.plugin = _make_plugin_registry(
            xep_0106=_mock_jid_escape_plugin(),
            xep_0047=ibb_plugin,
        )

        # Act / Assert — must not raise
        await comp.send_file_as_user("d1", "peer@example.com", b"data", "Nick")
