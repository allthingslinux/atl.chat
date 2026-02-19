"""Test identity resolver functionality."""

import pytest
from unittest.mock import AsyncMock

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
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.return_value = None
        resolver = IdentityResolver(client=mock_client)

        # Act
        result = await resolver.has_irc("123")

        # Assert
        assert result is False

