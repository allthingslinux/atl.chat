"""Tests for Discord adapter."""

from __future__ import annotations

import asyncio
import contextlib
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from bridge.events import (
    MessageDeleteOut,
    MessageIn,
    MessageOut,
    ReactionOut,
    TypingOut,
)
from bridge.gateway import Bus, ChannelRouter
from hypothesis import given
from hypothesis import strategies as st


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


def test_name_property(bus: Bus, router: ChannelRouter) -> None:
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    assert adapter.name == "discord"


def test_accept_event_all_types(bus: Bus, router: ChannelRouter) -> None:
    """Adapter accepts MessageOut, MessageDeleteOut, ReactionOut, TypingOut for discord target."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    assert adapter.accept_event("relay", MessageOut("discord", "123", "u1", "A", "hi", "m1"))
    assert adapter.accept_event("relay", MessageDeleteOut("discord", "123", "m1"))
    assert adapter.accept_event("relay", ReactionOut("discord", "123", "m1", "👍", "u1", "U"))
    assert adapter.accept_event("relay", TypingOut("discord", "123"))
    assert not adapter.accept_event("relay", MessageOut("irc", "123", "u1", "A", "hi", "m1"))
    assert not adapter.accept_event("relay", MessageIn("discord", "123", "u1", "A", "hi", "m1"))


def test_push_event_queues_message_out(bus: Bus, router: ChannelRouter) -> None:
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    evt = MessageOut("discord", "123", "u1", "Alice", "hi", "m1")
    adapter.push_event("relay", evt)
    assert adapter._queue.qsize() == 1
    assert adapter._queue.get_nowait() == evt


def test_is_bridged_channel(bus: Bus, router: ChannelRouter) -> None:
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    assert adapter._is_bridged_channel("123") is True
    assert adapter._is_bridged_channel("999") is False
    assert adapter._is_bridged_channel("123") is True  # int-like string


def test_resolve_discord_message_id_from_xmpp(bus: Bus, router: ChannelRouter) -> None:
    from bridge.adapters.discord import DiscordAdapter
    from bridge.adapters.xmpp import XMPPMessageIDTracker
    from bridge.gateway.msgid_resolver import DefaultMessageIDResolver

    mock_component = MagicMock()
    mock_component._msgid_tracker = XMPPMessageIDTracker()
    mock_component._msgid_tracker.store("orig-1", "discord-999", "room@conf.example.com")

    resolver = DefaultMessageIDResolver()
    resolver.register_xmpp(mock_component)

    adapter = DiscordAdapter(bus, router, identity_resolver=None, msgid_resolver=resolver)
    result = adapter._resolve_discord_message_id("orig-1", "xmpp")
    assert result == "discord-999"
    assert adapter._resolve_discord_message_id("unknown", "xmpp") is None


def test_resolve_discord_message_id_from_irc(bus: Bus, router: ChannelRouter) -> None:
    from bridge.adapters.discord import DiscordAdapter
    from bridge.adapters.irc import IRCAdapter
    from bridge.gateway.msgid_resolver import DefaultMessageIDResolver

    irc = IRCAdapter(bus, router, identity_resolver=None)
    irc._msgid_tracker.store("irc-msg-1", "discord-888")

    resolver = DefaultMessageIDResolver()
    resolver.register_irc(irc._msgid_tracker)

    adapter = DiscordAdapter(bus, router, identity_resolver=None, msgid_resolver=resolver)
    result = adapter._resolve_discord_message_id("irc-msg-1", "irc")
    assert result == "discord-888"
    assert adapter._resolve_discord_message_id("unknown", "irc") is None


def test_resolve_discord_message_id_unknown_origin_returns_none(bus: Bus, router: ChannelRouter) -> None:
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    assert adapter._resolve_discord_message_id("x", "unknown") is None


@pytest.mark.asyncio
async def test_on_message_skips_bot(bus: Bus, router: ChannelRouter) -> None:
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    adapter._bot = MagicMock()
    published = []
    bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

    msg = MagicMock()
    msg.author.bot = True
    msg.webhook_id = None
    msg.channel.id = 123
    msg.content = "hi"
    msg.attachments = []
    await adapter._on_message(msg)
    assert len(published) == 0


@pytest.mark.asyncio
async def test_on_message_skips_unbridged_channel(bus: Bus, router: ChannelRouter) -> None:
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    adapter._bot = MagicMock()
    published = []
    bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

    msg = MagicMock()
    msg.author.bot = False
    msg.webhook_id = None
    msg.channel.id = 999
    msg.content = "hi"
    msg.attachments = []
    msg.author.id = 1
    msg.author.display_name = "U"
    msg.author.name = "U"
    msg.author.display_avatar.url = None
    msg.id = 1
    msg.reference = None
    await adapter._on_message(msg)
    assert len(published) == 0


@pytest.mark.asyncio
async def test_on_message_includes_reply_to_id(bus: Bus, router: ChannelRouter) -> None:
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    adapter._bot = MagicMock()
    published = []
    bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

    msg = MagicMock()
    msg.author.bot = False
    msg.webhook_id = None
    msg.channel.id = 123
    msg.content = "reply"
    msg.attachments = []
    msg.author.id = 111
    msg.author.display_name = "Alice"
    msg.author.name = "Alice"
    msg.author.display_avatar.url = "https://x/av.png"
    msg.id = 777
    msg.reference = MagicMock()
    msg.reference.message_id = 555
    msg.type = discord.MessageType.default
    msg.flags = MagicMock(voice=False, value=0)
    await adapter._on_message(msg)
    assert len(published) == 1
    assert published[0][1].reply_to_id == "555"


@pytest.mark.asyncio
async def test_on_message_edit_publishes_with_is_edit(bus: Bus, router: ChannelRouter) -> None:
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    published = []
    bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

    message = MagicMock()
    message.author.bot = False
    message.webhook_id = None
    message.channel.id = 123
    message.content = "edited"
    message.author.id = 111
    message.author.display_name = "Alice"
    message.author.name = "Alice"
    message.author.display_avatar.url = None
    message.id = 777
    message.reference = None

    payload = MagicMock()
    payload.channel_id = 123
    payload.message = message

    await adapter._on_raw_message_edit(payload)
    assert len(published) == 1
    assert published[0][1].is_edit is True
    assert published[0][1].content == "edited"


@pytest.mark.asyncio
async def test_on_message_edit_skips_bot(bus: Bus, router: ChannelRouter) -> None:
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    published = []
    bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

    message = MagicMock()
    message.author.bot = True
    message.channel.id = 123
    message.content = "x"

    payload = MagicMock()
    payload.channel_id = 123
    payload.message = message

    await adapter._on_raw_message_edit(payload)
    assert len(published) == 0


@pytest.mark.asyncio
async def test_on_message_delete_publishes(bus: Bus, router: ChannelRouter) -> None:
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    published = []
    bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

    payload = MagicMock()
    payload.channel_id = 123
    payload.message_id = 999
    payload.cached_message = MagicMock()
    payload.cached_message.author.id = 111

    await adapter._on_raw_message_delete(payload)
    assert len(published) == 1
    assert published[0][0] == "discord"
    assert published[0][1].message_id == "999"
    assert published[0][1].origin == "discord"
    assert published[0][1].channel_id == "123"


@pytest.mark.asyncio
async def test_on_message_delete_skips_unbridged(bus: Bus, router: ChannelRouter) -> None:
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    published = []
    bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

    payload = MagicMock()
    payload.channel_id = 999
    payload.message_id = 1
    payload.cached_message = None

    await adapter._on_raw_message_delete(payload)
    assert len(published) == 0


@pytest.mark.asyncio
async def test_queue_consumer_edits_when_resolve_succeeds(bus: Bus, router: ChannelRouter) -> None:
    """When replace_id resolves, queue consumer calls _webhook_edit instead of send."""
    from bridge.adapters.discord import DiscordAdapter
    from bridge.adapters.irc import IRCAdapter
    from bridge.gateway.msgid_resolver import DefaultMessageIDResolver

    irc = IRCAdapter(bus, router, identity_resolver=None)
    irc._msgid_tracker.store("orig-123", "55555")

    resolver = DefaultMessageIDResolver()
    resolver.register_irc(irc._msgid_tracker)

    adapter = DiscordAdapter(bus, router, identity_resolver=None, msgid_resolver=resolver)
    adapter._bot = MagicMock()
    mock_webhook = MagicMock()
    mock_webhook.send = AsyncMock(return_value=MagicMock(id=99999))
    mock_webhook.edit_message = AsyncMock()
    adapter._get_or_create_webhook = AsyncMock(return_value=mock_webhook)

    evt = MessageOut(
        "discord",
        "123",
        "u1",
        "Alice",
        "edited content",
        "new-msg-id",
        raw={"is_edit": True, "replace_id": "orig-123", "origin": "irc"},
    )
    adapter._queue.put_nowait(evt)
    consumer = asyncio.create_task(adapter._queue_consumer(delay=0.01))
    await asyncio.sleep(0.05)
    consumer.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await consumer

    mock_webhook.edit_message.assert_called_once()
    assert mock_webhook.edit_message.call_args[0][0] == 55555
    assert mock_webhook.edit_message.call_args[1]["content"] == "edited content"
    mock_webhook.send.assert_not_called()


@pytest.mark.asyncio
async def test_queue_consumer_fetches_media_url_and_sends_file(bus: Bus, router: ChannelRouter) -> None:
    """When content is media-only URL, fetch to temp file and send as discord.File."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    adapter._bot = MagicMock()
    mock_webhook = MagicMock()
    mock_webhook.send = AsyncMock(return_value=MagicMock(id=11111))
    adapter._get_or_create_webhook = AsyncMock(return_value=mock_webhook)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        tf.write(b"fake image bytes")
        temp_path = tf.name

    from discord import File

    file_obj = File(temp_path, filename="image.png")

    async def mock_prepare(content: str):
        return ("", file_obj, temp_path)

    adapter._prepare_media = mock_prepare

    evt = MessageOut(
        "discord",
        "123",
        "u1",
        "Alice",
        "https://example.com/image.png",
        "m1",
    )
    adapter._queue.put_nowait(evt)
    consumer = asyncio.create_task(adapter._queue_consumer(delay=0.01))
    await asyncio.sleep(0.05)
    consumer.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await consumer

    mock_webhook.send.assert_called_once()
    call_kw = mock_webhook.send.call_args[1]
    assert call_kw.get("content") in (None, "")  # webhook sends None when content empty
    assert "file" in call_kw
    sent_file = call_kw["file"]
    assert sent_file.filename == "image.png"

    import os

    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.mark.asyncio
async def test_queue_consumer_resolves_mentions_before_send(bus: Bus, router: ChannelRouter) -> None:
    """@nick in content is resolved to <@userId> when guild has matching member."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    adapter._bot = MagicMock()
    mock_webhook = MagicMock()
    mock_webhook.send = AsyncMock(return_value=MagicMock(id=33333))
    adapter._get_or_create_webhook = AsyncMock(return_value=mock_webhook)

    member = MagicMock()
    member.id = 98765
    member.nick = "ircuser"
    member.display_name = "IRCUser"
    member.name = "ircuser"

    mock_channel = MagicMock()
    mock_channel.guild = MagicMock()
    mock_channel.guild.members = [member]
    adapter._bot.get_channel.return_value = mock_channel

    evt = MessageOut("discord", "123", "u1", "Alice", "Hey @ircuser check this", "m1")
    adapter._queue.put_nowait(evt)
    consumer = asyncio.create_task(adapter._queue_consumer(delay=0.01))
    await asyncio.sleep(0.05)
    consumer.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await consumer

    mock_webhook.send.assert_called_once()
    call_kw = mock_webhook.send.call_args[1]
    assert call_kw["content"] == "Hey <@98765> check this"


@pytest.mark.asyncio
async def test_queue_consumer_media_fetch_failure_falls_back_to_url(bus: Bus, router: ChannelRouter) -> None:
    """When media fetch fails, send URL as content (fallback)."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    adapter._bot = MagicMock()
    mock_webhook = MagicMock()
    mock_webhook.send = AsyncMock(return_value=MagicMock(id=22222))
    adapter._get_or_create_webhook = AsyncMock(return_value=mock_webhook)

    async def mock_prepare(content: str):
        return (content, None, None)

    adapter._prepare_media = mock_prepare

    url = "https://example.com/broken.png"
    evt = MessageOut("discord", "123", "u1", "Alice", url, "m1")
    adapter._queue.put_nowait(evt)
    consumer = asyncio.create_task(adapter._queue_consumer(delay=0.01))
    await asyncio.sleep(0.05)
    consumer.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await consumer

    mock_webhook.send.assert_called_once()
    call_kw = mock_webhook.send.call_args[1]
    assert call_kw["content"] == url
    assert call_kw.get("file") is None


@pytest.mark.asyncio
async def test_edit_fallback_to_send_when_resolve_fails(bus: Bus, router: ChannelRouter) -> None:
    """When replace_id cannot be resolved, edit is skipped and message is sent as new."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    adapter._bot = MagicMock()
    mock_webhook = MagicMock()
    mock_webhook.send = AsyncMock(return_value=MagicMock(id=12345))
    adapter._get_or_create_webhook = AsyncMock(return_value=mock_webhook)
    bus._dispatcher._targets = []

    evt = MessageOut(
        "discord",
        "123",
        "u1",
        "Alice",
        "corrected",
        "corr-2",
        raw={"is_edit": True, "replace_id": "unknown", "origin": "xmpp"},
    )
    adapter._queue.put_nowait(evt)
    consumer = asyncio.create_task(adapter._queue_consumer(delay=0.01))
    await asyncio.sleep(0.05)
    consumer.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await consumer

    mock_webhook.send.assert_called_once()
    mock_webhook.edit_message.assert_not_called()


@pytest.mark.asyncio
async def test_webhook_messages_are_skipped_to_prevent_echo(bus: Bus, router: ChannelRouter) -> None:
    """Messages from webhooks (our bridge output) must not be republished to prevent echo loops."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    adapter._bot = MagicMock()
    published = []

    def capture(source: str, evt: object) -> None:
        published.append((source, evt))

    bus.publish = capture  # type: ignore[method-assign]

    msg = MagicMock()
    msg.author.bot = False
    msg.webhook_id = 99999
    msg.channel.id = 123
    msg.content = "bridge relayed this"
    msg.attachments = []
    msg.author.id = 1
    msg.author.display_name = "User"
    msg.author.name = "User"
    msg.author.display_avatar.url = None
    msg.id = 888
    msg.reference = None

    await adapter._on_message(msg)

    assert len(published) == 0


@pytest.mark.asyncio
async def test_regular_messages_are_published(bus: Bus, router: ChannelRouter) -> None:
    """Regular Discord messages (no webhook_id) are published to the bus."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    adapter._bot = MagicMock()
    published = []

    def capture(source: str, evt: object) -> None:
        published.append((source, evt))

    bus.publish = capture  # type: ignore[method-assign]

    msg = MagicMock()
    msg.author.bot = False
    msg.webhook_id = None
    msg.channel.id = 123
    msg.content = "hello"
    msg.attachments = []
    msg.author.id = 111
    msg.author.display_name = "Alice"
    msg.author.name = "Alice"
    msg.author.display_avatar.url = "https://cdn.example/av.png"
    msg.id = 777
    msg.reference = None
    msg.type = discord.MessageType.default
    msg.flags = MagicMock(voice=False, value=0)

    await adapter._on_message(msg)

    assert len(published) == 1
    assert published[0][0] == "discord"
    assert published[0][1].content == "hello"


def test_discord_adapter_accepts_message_out_for_discord(bus: Bus, router: ChannelRouter) -> None:
    """Discord adapter accepts MessageOut with target_origin=discord."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    assert adapter.accept_event("irc", MessageOut("discord", "123", "u1", "Alice", "hi", "m1"))
    assert not adapter.accept_event("irc", MessageOut("irc", "123", "u1", "Alice", "hi", "m1"))
    assert not adapter.accept_event("irc", MessageIn("irc", "123", "u1", "Alice", "hi", "m1"))


def test_ensure_valid_username() -> None:
    """Webhook usernames are 2-32 chars (AUDIT §3)."""
    from bridge.adapters.discord import _ensure_valid_username

    assert len(_ensure_valid_username("A")) >= 2
    assert len(_ensure_valid_username("x" * 50)) == 32
    assert _ensure_valid_username("Alice") == "Alice"


@pytest.mark.asyncio
async def test_push_event_triggers_handle_delete_out(bus: Bus, router: ChannelRouter) -> None:
    """push_event(MessageDeleteOut) schedules _handle_delete_out."""
    from bridge.adapters.discord import DiscordAdapter
    from bridge.adapters.discord import outbound as discord_outbound

    with patch.object(discord_outbound, "TextChannel", MagicMock):
        adapter = DiscordAdapter(bus, router, identity_resolver=None)
        adapter._bot = MagicMock()
        mock_channel = MagicMock()
        mock_msg = MagicMock()
        mock_msg.delete = AsyncMock()
        adapter._bot.get_channel.return_value = mock_channel
        mock_channel.fetch_message = AsyncMock(return_value=mock_msg)

        evt = MessageDeleteOut("discord", "123", "999")
        adapter.push_event("relay", evt)
        await asyncio.sleep(0.1)  # Let the task run

        mock_channel.fetch_message.assert_called_once_with(999)
        mock_msg.delete.assert_called_once()


@pytest.mark.asyncio
async def test_handle_delete_out_no_bot_returns_early(bus: Bus, router: ChannelRouter) -> None:
    """_handle_delete_out does nothing when _bot is None."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    adapter._bot = None
    evt = MessageDeleteOut("discord", "123", "msg-1")
    await adapter._handle_delete_out(evt)
    # No exception, no calls


@pytest.mark.asyncio
async def test_handle_reaction_out_adds_reaction(bus: Bus, router: ChannelRouter) -> None:
    """_handle_reaction_out adds emoji to Discord message."""
    from bridge.adapters.discord import DiscordAdapter
    from bridge.adapters.discord import outbound as discord_outbound

    with patch.object(discord_outbound, "TextChannel", MagicMock):
        adapter = DiscordAdapter(bus, router, identity_resolver=None)
        adapter._bot = MagicMock()
        mock_channel = MagicMock()
        mock_msg = MagicMock()
        mock_msg.add_reaction = AsyncMock()
        adapter._bot.get_channel.return_value = mock_channel
        mock_channel.fetch_message = AsyncMock(return_value=mock_msg)

        evt = ReactionOut("discord", "123", "888", "👍", "u1", "Alice")
        await adapter._handle_reaction_out(evt)

        mock_msg.add_reaction.assert_called_once_with("👍")


@pytest.mark.asyncio
async def test_handle_typing_out_triggers_typing(bus: Bus, router: ChannelRouter) -> None:
    """_handle_typing_out triggers channel.typing()."""
    from bridge.adapters.discord import DiscordAdapter
    from bridge.adapters.discord import outbound as discord_outbound

    with patch.object(discord_outbound, "TextChannel", MagicMock), patch("asyncio.sleep", AsyncMock()):
        adapter = DiscordAdapter(bus, router, identity_resolver=None)
        adapter._bot = MagicMock()
        mock_channel = MagicMock()
        mock_typing = MagicMock()
        mock_typing.__aenter__ = AsyncMock(return_value=None)
        mock_typing.__aexit__ = AsyncMock(return_value=None)
        mock_channel.typing.return_value = mock_typing
        adapter._bot.get_channel.return_value = mock_channel

        evt = TypingOut("discord", "123")
        await adapter._handle_typing_out(evt)

        mock_channel.typing.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_send_returns_message_id(bus: Bus, router: ChannelRouter) -> None:
    """_webhook_send returns Discord message ID when successful."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    mock_webhook = MagicMock()
    mock_webhook.send = AsyncMock(return_value=MagicMock(id=99999))
    adapter._get_or_create_webhook = AsyncMock(return_value=mock_webhook)

    result = await adapter._webhook_send("123", "Alice", "hello")
    assert result == 99999
    mock_webhook.send.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_send_none_when_no_webhook(bus: Bus, router: ChannelRouter) -> None:
    """_webhook_send returns None when _get_or_create_webhook returns None."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    adapter._get_or_create_webhook = AsyncMock(return_value=None)

    result = await adapter._webhook_send("123", "Alice", "hello")
    assert result is None


@pytest.mark.asyncio
async def test_webhook_edit_succeeds(bus: Bus, router: ChannelRouter) -> None:
    """_webhook_edit returns True when edit succeeds."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    mock_webhook = MagicMock()
    mock_webhook.edit_message = AsyncMock()
    adapter._get_or_create_webhook = AsyncMock(return_value=mock_webhook)

    result = await adapter._webhook_edit("123", 88888, "edited")
    assert result is True
    mock_webhook.edit_message.assert_called_once()
    call_args = mock_webhook.edit_message.call_args
    assert call_args[0][0] == 88888
    assert call_args[1]["content"] == "edited"


@pytest.mark.asyncio
async def test_on_reaction_add_publishes_unicode_emoji(bus: Bus, router: ChannelRouter) -> None:
    """_on_reaction_add publishes ReactionIn for unicode emoji."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    published = []
    bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

    payload = MagicMock()
    payload.emoji.is_unicode_emoji.return_value = True
    payload.emoji.__str__ = lambda self: "👍"
    payload.channel_id = 123
    payload.message_id = 456
    payload.user_id = 789
    payload.member = MagicMock()
    payload.member.display_name = "Alice"
    payload.type = discord.enums.ReactionType.normal

    await adapter._on_reaction_add(payload)

    assert len(published) == 1
    evt = published[0][1]
    assert evt.origin == "discord"
    assert evt.channel_id == "123"
    assert evt.message_id == "456"
    assert evt.emoji == "👍"
    assert evt.author_display == "Alice"


@pytest.mark.asyncio
async def test_on_reaction_add_skips_custom_emoji(bus: Bus, router: ChannelRouter) -> None:
    """_on_reaction_add does not publish for custom Discord emoji."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    published = []
    bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

    payload = MagicMock()
    payload.emoji.is_unicode_emoji.return_value = False

    await adapter._on_reaction_add(payload)

    assert len(published) == 0


@pytest.mark.asyncio
async def test_on_typing_publishes_when_bridged(bus: Bus, router: ChannelRouter) -> None:
    """_on_typing publishes TypingIn for bridged channel."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    published = []
    bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

    channel = MagicMock()
    channel.id = 123
    user = MagicMock()
    user.bot = False
    user.id = 999

    await adapter._on_typing(channel, user)

    assert len(published) == 1
    assert published[0][1].origin == "discord"
    assert published[0][1].channel_id == "123"
    assert published[0][1].user_id == "999"


@pytest.mark.asyncio
async def test_on_typing_skips_bot(bus: Bus, router: ChannelRouter) -> None:
    """_on_typing does not publish when user is bot."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    published = []
    bus.publish = lambda s, e: published.append((s, e))  # type: ignore[method-assign]

    channel = MagicMock()
    channel.id = 123
    user = MagicMock()
    user.bot = True

    await adapter._on_typing(channel, user)

    assert len(published) == 0


@pytest.mark.asyncio
async def test_upload_file_sends_to_channel(bus: Bus, router: ChannelRouter) -> None:
    """upload_file sends file to Discord channel."""
    from bridge.adapters.discord import DiscordAdapter
    from bridge.adapters.discord import media as discord_media

    with patch.object(discord_media, "TextChannel", MagicMock):
        adapter = DiscordAdapter(bus, router, identity_resolver=None)
        adapter._bot = MagicMock()
        mock_channel = MagicMock()
        mock_channel.send = AsyncMock()
        adapter._bot.get_channel.return_value = mock_channel

        await adapter.upload_file("123", b"file content", "test.txt")

        mock_channel.send.assert_called_once()
        call_kw = mock_channel.send.call_args[1]
        assert "file" in call_kw


@pytest.mark.asyncio
async def test_upload_file_no_bot_returns_early(bus: Bus, router: ChannelRouter) -> None:
    """upload_file does nothing when _bot is None."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    adapter._bot = None
    await adapter.upload_file("123", b"x", "a.txt")
    # No exception


@pytest.mark.asyncio
async def test_cmd_bridge_status_replies_with_identity(bus: Bus, router: ChannelRouter) -> None:
    """_cmd_bridge_status replies with IRC/XMPP link status when identity configured."""
    from bridge.adapters.discord import DiscordAdapter

    mock_identity = MagicMock()
    mock_identity.discord_to_irc = AsyncMock(return_value="ircnick")
    mock_identity.discord_to_xmpp = AsyncMock(return_value="user@example.com")

    adapter = DiscordAdapter(bus, router, identity_resolver=mock_identity)
    ctx = MagicMock()
    ctx.guild = MagicMock()
    ctx.author = MagicMock()
    ctx.author.id = 111
    ctx.reply = AsyncMock()

    await adapter._cmd_bridge_status(ctx)

    ctx.reply.assert_called_once()
    reply_text = ctx.reply.call_args[0][0]
    assert "IRC: ircnick" in reply_text
    assert "XMPP: user@example.com" in reply_text


@pytest.mark.asyncio
async def test_cmd_bridge_status_no_identity(bus: Bus, router: ChannelRouter) -> None:
    """_cmd_bridge_status replies with 'not configured' when no identity resolver."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    ctx = MagicMock()
    ctx.guild = MagicMock()
    ctx.author = MagicMock()
    ctx.reply = AsyncMock()

    await adapter._cmd_bridge_status(ctx)

    ctx.reply.assert_called_once_with("Identity resolution not configured (Portal).")


@pytest.mark.asyncio
async def test_cmd_bridge_status_no_guild_returns_early(bus: Bus, router: ChannelRouter) -> None:
    """_cmd_bridge_status returns without replying when ctx.guild is None."""
    from bridge.adapters.discord import DiscordAdapter

    mock_identity = MagicMock()
    adapter = DiscordAdapter(bus, router, identity_resolver=mock_identity)
    ctx = MagicMock()
    ctx.guild = None
    ctx.author = MagicMock()
    ctx.reply = AsyncMock()

    await adapter._cmd_bridge_status(ctx)

    ctx.reply.assert_not_called()


# ---------------------------------------------------------------------------
# Task 7.5 – Per-channel locks and media preparation
# ---------------------------------------------------------------------------


def test_get_channel_lock_same_instance(bus: Bus, router: ChannelRouter) -> None:
    """_get_channel_lock returns the same Lock for the same channel ID."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    lock_a1 = adapter._get_channel_lock("A")
    lock_a2 = adapter._get_channel_lock("A")
    assert lock_a1 is lock_a2


def test_get_channel_lock_different_instances(bus: Bus, router: ChannelRouter) -> None:
    """_get_channel_lock returns independent Locks for different channel IDs."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    lock_a = adapter._get_channel_lock("A")
    lock_b = adapter._get_channel_lock("B")
    assert lock_a is not lock_b


@pytest.mark.asyncio
async def test_prepare_media_non_media_content(bus: Bus, router: ChannelRouter) -> None:
    """_prepare_media returns (content, None, None) for non-media text."""
    from bridge.adapters.discord import DiscordAdapter

    adapter = DiscordAdapter(bus, router, identity_resolver=None)
    content = "just a regular message, no URL"
    result = await adapter._prepare_media(content)
    assert result == (content, None, None)


@pytest.mark.asyncio
async def test_prepare_media_fallback_on_fetch_failure(bus: Bus, router: ChannelRouter) -> None:
    """_prepare_media falls back to (content, None, None) when media fetch fails."""
    from bridge.adapters.discord import DiscordAdapter
    from bridge.adapters.discord import media as discord_media

    adapter = DiscordAdapter(bus, router, identity_resolver=None)

    url = "https://example.com/photo.png"
    with patch.object(discord_media, "fetch_media_to_temp", AsyncMock(return_value=None)):
        result = await adapter._prepare_media(url)
    assert result == (url, None, None)


# ---------------------------------------------------------------------------
# Task 7.6 – Property test: per-channel lock isolation
# ---------------------------------------------------------------------------


class TestChannelLockIsolationProperty:
    """Property 4: Per-channel lock isolation.

    **Validates: Requirements 5.4, 5.5**

    For any two distinct channel IDs a and b, _get_channel_lock(a) is not
    _get_channel_lock(b).  For any channel ID c, repeated calls return the
    same asyncio.Lock instance.
    """

    @staticmethod
    def _make_adapter():
        from bridge.adapters.discord import DiscordAdapter

        bus = Bus()
        router = ChannelRouter()
        router.load_from_config({"mappings": []})
        return DiscordAdapter(bus, router, identity_resolver=None)

    @given(channel_id=st.text(min_size=1))
    def test_same_id_returns_same_lock(self, channel_id: str) -> None:
        """Repeated calls with the same channel ID return the identical Lock."""
        adapter = self._make_adapter()
        lock1 = adapter._get_channel_lock(channel_id)
        lock2 = adapter._get_channel_lock(channel_id)
        assert lock1 is lock2
        assert isinstance(lock1, asyncio.Lock)

    @given(data=st.data())
    def test_distinct_ids_return_different_locks(self, data: st.DataObject) -> None:
        """Two distinct channel IDs always yield independent Lock instances."""
        a = data.draw(st.text(min_size=1), label="channel_a")
        b = data.draw(st.text(min_size=1).filter(lambda x: x != a), label="channel_b")
        adapter = self._make_adapter()
        assert adapter._get_channel_lock(a) is not adapter._get_channel_lock(b)

    @given(channel_id=st.text(min_size=1), n=st.integers(min_value=2, max_value=20))
    def test_repeated_calls_always_same_instance(self, channel_id: str, n: int) -> None:
        """Calling _get_channel_lock N times for the same ID always returns one Lock."""
        adapter = self._make_adapter()
        first = adapter._get_channel_lock(channel_id)
        for _ in range(n - 1):
            assert adapter._get_channel_lock(channel_id) is first
