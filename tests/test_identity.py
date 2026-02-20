"""Test identity resolver functionality."""

from unittest.mock import AsyncMock

import pytest

from bridge.identity import IdentityResolver, PortalClient


class TestIdentityResolver:
    """Test identity resolution and caching."""

    @pytest.mark.asyncio
    async def test_discord_to_irc(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.return_value = {
            "discord_id": "123",
            "irc_nick": "testuser",
        }
        resolver = IdentityResolver(client=mock_client)

        # Act
        irc_nick = await resolver.discord_to_irc("123")

        # Assert
        assert irc_nick == "testuser"
        mock_client.get_identity_by_discord.assert_called_once_with("123")

    @pytest.mark.asyncio
    async def test_discord_to_irc_returns_none_when_not_found(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.return_value = None
        resolver = IdentityResolver(client=mock_client)

        # Act
        result = await resolver.discord_to_irc("unknown")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_caching_reduces_api_calls(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.return_value = {
            "discord_id": "123",
            "irc_nick": "testuser",
        }
        resolver = IdentityResolver(client=mock_client, ttl=60)

        # Act
        result1 = await resolver.discord_to_irc("123")
        result2 = await resolver.discord_to_irc("123")

        # Assert
        assert result1 == result2 == "testuser"
        mock_client.get_identity_by_discord.assert_called_once()  # Only called once due to cache

    @pytest.mark.asyncio
    async def test_cache_expiry(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.return_value = {
            "discord_id": "123",
            "irc_nick": "testuser",
        }
        resolver = IdentityResolver(client=mock_client, ttl=0)  # Immediate expiry

        # Act
        await resolver.discord_to_irc("123")
        await resolver.discord_to_irc("123")

        # Assert
        # With TTL=0, cache expires immediately, so called twice
        assert mock_client.get_identity_by_discord.call_count == 2

    @pytest.mark.asyncio
    async def test_irc_to_discord(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_irc_nick.return_value = {
            "discord_id": "123",
            "irc_nick": "testuser",
        }
        resolver = IdentityResolver(client=mock_client)

        # Act
        discord_id = await resolver.irc_to_discord("testuser")

        # Assert
        assert discord_id == "123"
        mock_client.get_identity_by_irc_nick.assert_called_once_with("testuser", server=None)

    @pytest.mark.asyncio
    async def test_xmpp_to_discord(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_xmpp_jid.return_value = {
            "discord_id": "123",
            "xmpp_jid": "user@example.com",
        }
        resolver = IdentityResolver(client=mock_client)

        # Act
        discord_id = await resolver.xmpp_to_discord("user@example.com")

        # Assert
        assert discord_id == "123"

    @pytest.mark.asyncio
    async def test_has_irc_returns_true_when_linked(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.return_value = {
            "discord_id": "123",
            "irc_nick": "testuser",
        }
        resolver = IdentityResolver(client=mock_client)

        # Act
        result = await resolver.has_irc("123")

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_has_irc_returns_false_when_not_linked(self):
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.return_value = None
        resolver = IdentityResolver(client=mock_client)
        assert await resolver.has_irc("123") is False


class TestDiscordToXmpp:
    @pytest.mark.asyncio
    async def test_discord_to_xmpp(self):
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.return_value = {"discord_id": "123", "xmpp_jid": "user@example.com"}
        resolver = IdentityResolver(client=mock_client)
        assert await resolver.discord_to_xmpp("123") == "user@example.com"

    @pytest.mark.asyncio
    async def test_discord_to_xmpp_returns_none_when_not_found(self):
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.return_value = None
        resolver = IdentityResolver(client=mock_client)
        assert await resolver.discord_to_xmpp("unknown") is None

    @pytest.mark.asyncio
    async def test_discord_to_xmpp_shares_cache_with_discord_to_irc(self):
        """discord_to_irc and discord_to_xmpp use the same cache key — one API call serves both."""
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.return_value = {
            "discord_id": "123", "irc_nick": "user", "xmpp_jid": "user@example.com"
        }
        resolver = IdentityResolver(client=mock_client)
        await resolver.discord_to_irc("123")
        result = await resolver.discord_to_xmpp("123")
        assert result == "user@example.com"
        mock_client.get_identity_by_discord.assert_called_once()


class TestHasXmpp:
    @pytest.mark.asyncio
    async def test_has_xmpp_returns_true_when_linked(self):
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.return_value = {"xmpp_jid": "user@example.com"}
        resolver = IdentityResolver(client=mock_client)
        assert await resolver.has_xmpp("123") is True

    @pytest.mark.asyncio
    async def test_has_xmpp_returns_false_when_not_linked(self):
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.return_value = None
        resolver = IdentityResolver(client=mock_client)
        assert await resolver.has_xmpp("123") is False


class TestIrcToDiscordWithServer:
    @pytest.mark.asyncio
    async def test_irc_to_discord_with_server(self):
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_irc_nick.return_value = {"discord_id": "456"}
        resolver = IdentityResolver(client=mock_client)
        result = await resolver.irc_to_discord("nick", "irc.libera.chat")
        assert result == "456"
        mock_client.get_identity_by_irc_nick.assert_called_once_with("nick", server="irc.libera.chat")

    @pytest.mark.asyncio
    async def test_irc_to_discord_cache_hit(self):
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_irc_nick.return_value = {"discord_id": "456"}
        resolver = IdentityResolver(client=mock_client)
        await resolver.irc_to_discord("nick")
        await resolver.irc_to_discord("nick")
        mock_client.get_identity_by_irc_nick.assert_called_once()


class TestXmppToDiscordCache:
    @pytest.mark.asyncio
    async def test_xmpp_to_discord_cache_hit(self):
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_xmpp_jid.return_value = {"discord_id": "789"}
        resolver = IdentityResolver(client=mock_client)
        await resolver.xmpp_to_discord("user@example.com")
        await resolver.xmpp_to_discord("user@example.com")
        mock_client.get_identity_by_xmpp_jid.assert_called_once()


class TestPortalClientHeaders:
    def test_headers_without_token(self):
        client = PortalClient("https://portal.example.com")
        headers = client._headers()
        assert headers == {"Accept": "application/json"}
        assert "Authorization" not in headers

    def test_headers_with_token(self):
        client = PortalClient("https://portal.example.com", token="secret")
        headers = client._headers()
        assert headers["Authorization"] == "Bearer secret"
        assert headers["Accept"] == "application/json"

