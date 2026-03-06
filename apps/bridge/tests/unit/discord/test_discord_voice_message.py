"""Tests for Discord voice message handling (Requirements 21.1, 21.2).

Verifies that voice messages relay the audio attachment URL when available,
fall back to a ``[voice message]`` placeholder when no attachment is present,
and that non-voice messages are unaffected by the voice-message logic.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import discord
import pytest
from bridge.adapters.discord.handlers import _is_voice_message
from bridge.gateway import Bus, ChannelRouter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bus() -> Bus:
    return Bus()


@pytest.fixture
def router() -> ChannelRouter:
    r = ChannelRouter()
    r.load_from_config(
        {
            "mappings": [
                {
                    "discord_channel_id": "123",
                    "irc": {"server": "s", "port": 6667, "tls": False, "channel": "#c"},
                },
            ]
        }
    )
    return r


def _make_adapter(bus: Bus, router: ChannelRouter):
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    adapter._bot = MagicMock()
    adapter._bot.user.id = 42
    return adapter


def _make_message(*, channel_id: int = 123, voice: bool = False, attachments=None):
    """Build a mock Discord Message with configurable voice flag and attachments."""
    msg = MagicMock()
    msg.webhook_id = None
    msg.author.bot = False
    msg.author.id = 999
    msg.author.display_name = "TestUser"
    msg.author.name = "testuser"
    msg.author.display_avatar.url = "https://cdn.example.com/avatar.png"
    msg.channel.id = channel_id
    msg.id = 55555
    msg.content = ""
    msg.reference = None
    msg.type = discord.MessageType.default

    # Set up flags
    flags = MagicMock()
    flags.voice = voice
    flags.value = (1 << 13) if voice else 0
    msg.flags = flags

    msg.attachments = attachments or []
    return msg


# ---------------------------------------------------------------------------
# _is_voice_message — unit tests
# ---------------------------------------------------------------------------


class TestIsVoiceMessage:
    """Unit tests for the _is_voice_message helper."""

    def test_voice_flag_true(self) -> None:
        msg = _make_message(voice=True)
        assert _is_voice_message(msg) is True

    def test_voice_flag_false(self) -> None:
        msg = _make_message(voice=False)
        assert _is_voice_message(msg) is False

    def test_no_flags_attribute(self) -> None:
        msg = MagicMock(spec=[])
        msg.author = MagicMock()
        assert _is_voice_message(msg) is False

    def test_fallback_bit_13(self) -> None:
        """When .voice attr is missing, fall back to bit 13 check."""
        msg = MagicMock()
        flags = MagicMock(spec=["value"])  # no .voice attribute
        flags.value = 1 << 13
        msg.flags = flags
        assert _is_voice_message(msg) is True

    def test_fallback_bit_13_not_set(self) -> None:
        msg = MagicMock()
        flags = MagicMock(spec=["value"])
        flags.value = 0
        msg.flags = flags
        assert _is_voice_message(msg) is False


# ---------------------------------------------------------------------------
# on_message — voice message with attachment
# ---------------------------------------------------------------------------


class TestVoiceMessageWithAttachment:
    """Voice messages with an audio attachment relay the attachment URL."""

    @pytest.mark.asyncio
    async def test_voice_with_attachment_relays_url(self, bus: Bus, router: ChannelRouter) -> None:
        adapter = _make_adapter(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        attachment = MagicMock()
        attachment.url = "https://cdn.discord.com/attachments/123/voice-message.ogg"
        attachment.proxy_url = "https://cdn.discord.com/attachments/123/voice-message.ogg"
        attachment.id = 77777

        msg = _make_message(voice=True, attachments=[attachment])

        await adapter._on_message(msg)

        assert len(published) == 1
        _, evt = published[0]
        assert evt.content == "https://cdn.discord.com/attachments/123/voice-message.ogg"


# ---------------------------------------------------------------------------
# on_message — voice message without attachment
# ---------------------------------------------------------------------------


class TestVoiceMessageWithoutAttachment:
    """Voice messages without attachments relay the placeholder text."""

    @pytest.mark.asyncio
    async def test_voice_without_attachment_relays_placeholder(self, bus: Bus, router: ChannelRouter) -> None:
        adapter = _make_adapter(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        msg = _make_message(voice=True, attachments=[])

        await adapter._on_message(msg)

        assert len(published) == 1
        _, evt = published[0]
        assert evt.content == "[voice message]"


# ---------------------------------------------------------------------------
# on_message — non-voice messages unaffected
# ---------------------------------------------------------------------------


class TestNonVoiceMessageUnaffected:
    """Non-voice messages go through the normal message handling path."""

    @pytest.mark.asyncio
    async def test_regular_message_not_treated_as_voice(self, bus: Bus, router: ChannelRouter) -> None:
        adapter = _make_adapter(bus, router)
        published: list = []
        bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

        msg = _make_message(voice=False)
        msg.content = "Hello, world!"

        await adapter._on_message(msg)

        assert len(published) == 1
        _, evt = published[0]
        # Content should be the original text, not a voice placeholder
        assert evt.content == "Hello, world!"
