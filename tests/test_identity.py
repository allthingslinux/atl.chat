"""Test identity resolver functionality."""

from unittest.mock import AsyncMock

import pytest

from bridge.identity import IdentityResolver, PortalClient


def make_resolver(return_value=None, *, method="get_identity_by_discord", ttl=3600):
    """Create a resolver with a pre-configured mock client."""
    client = AsyncMock(spec=PortalClient)
    getattr(client, method).return_value = return_value
    return client, IdentityResolver(client=client, ttl=ttl)


class TestIdentityResolver:
    """Test identity resolution and caching."""

    @pytest.mark.asyncio
    async def test_discord_to_irc(self):
        client, resolver = make_resolver({"discord_id": "123", "irc_nick": "testuser"})
        assert await resolver.discord_to_irc("123") == "testuser"
        client.get_identity_by_discord.assert_called_once_with("123")

    @pytest.mark.asyncio
    async def test_discord_to_irc_returns_none_when_not_found(self):
        _, resolver = make_resolver(None)
        assert await resolver.discord_to_irc("unknown") is None

    @pytest.mark.asyncio
    async def test_caching_reduces_api_calls(self):
        client, resolver = make_resolver({"discord_id": "123", "irc_nick": "testuser"}, ttl=60)
        result1 = await resolver.discord_to_irc("123")
        result2 = await resolver.discord_to_irc("123")
        assert result1 == result2 == "testuser"
        client.get_identity_by_discord.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_expiry(self):
        client, resolver = make_resolver({"discord_id": "123", "irc_nick": "testuser"}, ttl=0)
        await resolver.discord_to_irc("123")
        await resolver.discord_to_irc("123")
        assert client.get_identity_by_discord.call_count == 2

    @pytest.mark.asyncio
    async def test_irc_to_discord(self):
        client, resolver = make_resolver(
            {"discord_id": "123", "irc_nick": "testuser"},
            method="get_identity_by_irc_nick",
        )
        assert await resolver.irc_to_discord("testuser") == "123"
        client.get_identity_by_irc_nick.assert_called_once_with("testuser", server=None)

    @pytest.mark.asyncio
    async def test_xmpp_to_discord(self):
        _, resolver = make_resolver(
            {"discord_id": "123", "xmpp_jid": "user@example.com"},
            method="get_identity_by_xmpp_jid",
        )
        assert await resolver.xmpp_to_discord("user@example.com") == "123"

    @pytest.mark.asyncio
    async def test_has_irc_returns_true_when_linked(self):
        _, resolver = make_resolver({"discord_id": "123", "irc_nick": "testuser"})
        assert await resolver.has_irc("123") is True

    @pytest.mark.asyncio
    async def test_has_irc_returns_false_when_not_linked(self):
        _, resolver = make_resolver(None)
        assert await resolver.has_irc("123") is False


class TestDiscordToXmpp:
    @pytest.mark.asyncio
    async def test_discord_to_xmpp(self):
        _, resolver = make_resolver({"discord_id": "123", "xmpp_jid": "user@example.com"})
        assert await resolver.discord_to_xmpp("123") == "user@example.com"

    @pytest.mark.asyncio
    async def test_discord_to_xmpp_returns_none_when_not_found(self):
        _, resolver = make_resolver(None)
        assert await resolver.discord_to_xmpp("unknown") is None

    @pytest.mark.asyncio
    async def test_discord_to_xmpp_shares_cache_with_discord_to_irc(self):
        """discord_to_irc and discord_to_xmpp use the same cache key — one API call serves both."""
        client, resolver = make_resolver(
            {"discord_id": "123", "irc_nick": "user", "xmpp_jid": "user@example.com"}
        )
        await resolver.discord_to_irc("123")
        assert await resolver.discord_to_xmpp("123") == "user@example.com"
        client.get_identity_by_discord.assert_called_once()


class TestHasXmpp:
    @pytest.mark.asyncio
    async def test_has_xmpp_returns_true_when_linked(self):
        _, resolver = make_resolver({"xmpp_jid": "user@example.com"})
        assert await resolver.has_xmpp("123") is True

    @pytest.mark.asyncio
    async def test_has_xmpp_returns_false_when_not_linked(self):
        _, resolver = make_resolver(None)
        assert await resolver.has_xmpp("123") is False


class TestIrcToDiscordWithServer:
    @pytest.mark.asyncio
    async def test_irc_to_discord_with_server(self):
        client, resolver = make_resolver(
            {"discord_id": "456"}, method="get_identity_by_irc_nick"
        )
        assert await resolver.irc_to_discord("nick", "irc.libera.chat") == "456"
        client.get_identity_by_irc_nick.assert_called_once_with("nick", server="irc.libera.chat")

    @pytest.mark.asyncio
    async def test_irc_to_discord_cache_hit(self):
        client, resolver = make_resolver(
            {"discord_id": "456"}, method="get_identity_by_irc_nick"
        )
        await resolver.irc_to_discord("nick")
        await resolver.irc_to_discord("nick")
        client.get_identity_by_irc_nick.assert_called_once()


class TestXmppToDiscordCache:
    @pytest.mark.asyncio
    async def test_xmpp_to_discord_cache_hit(self):
        client, resolver = make_resolver(
            {"discord_id": "789"}, method="get_identity_by_xmpp_jid"
        )
        await resolver.xmpp_to_discord("user@example.com")
        await resolver.xmpp_to_discord("user@example.com")
        client.get_identity_by_xmpp_jid.assert_called_once()


class TestPortalClientHeaders:
    def test_headers_without_token(self):
        headers = PortalClient("https://portal.example.com")._headers()
        assert headers == {"Accept": "application/json"}
        assert "Authorization" not in headers

    def test_headers_with_token(self):
        headers = PortalClient("https://portal.example.com", token="secret")._headers()
        assert headers["Authorization"] == "Bearer secret"
        assert headers["Accept"] == "application/json"
