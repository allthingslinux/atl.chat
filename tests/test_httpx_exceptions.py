"""Test handling of httpx exceptions."""

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from bridge.identity import IdentityResolver, PortalClient


class TestHttpxExceptions:
    """Test handling of all httpx exception types."""

    @pytest.mark.asyncio
    async def test_connect_timeout(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.ConnectTimeout("Connection timed out")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.ConnectTimeout):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_read_timeout(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.ReadTimeout("Read timed out")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.ReadTimeout):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_write_timeout(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.WriteTimeout("Write timed out")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.WriteTimeout):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_pool_timeout(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.PoolTimeout("Pool exhausted")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.PoolTimeout):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_connect_error(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.ConnectError("Connection refused")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.ConnectError):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_read_error(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.ReadError("Read failed")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.ReadError):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_write_error(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.WriteError("Write failed")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.WriteError):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_close_error(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.CloseError("Close failed")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.CloseError):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_protocol_error(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.ProtocolError("Protocol error")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.ProtocolError):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_proxy_error(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.ProxyError("Proxy error")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.ProxyError):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_unsupported_protocol(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.UnsupportedProtocol("Unsupported")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.UnsupportedProtocol):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_decoding_error(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.DecodingError("Decoding failed")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.DecodingError):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_too_many_redirects(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.TooManyRedirects("Too many redirects")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.TooManyRedirects):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_http_status_error_404(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        request = Mock()
        response = Mock()
        response.status_code = 404
        mock_client.get_identity_by_discord.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=request, response=response
        )
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_http_status_error_500(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        request = Mock()
        response = Mock()
        response.status_code = 500
        mock_client.get_identity_by_discord.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error", request=request, response=response
        )
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_http_status_error_403(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        request = Mock()
        response = Mock()
        response.status_code = 403
        mock_client.get_identity_by_discord.side_effect = httpx.HTTPStatusError(
            "403 Forbidden", request=request, response=response
        )
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_invalid_url(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.InvalidURL("Invalid URL")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.InvalidURL):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_stream_error(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.StreamError("Stream error")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.StreamError):
            await resolver.discord_to_irc("123")
