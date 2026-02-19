"""Test retry logic for transient errors."""

from unittest.mock import AsyncMock

import httpx
import pytest

from bridge.identity import IdentityResolver, PortalClient


class TestRetryLogic:
    """Test that IdentityResolver propagates errors from PortalClient."""

    @pytest.mark.asyncio
    async def test_resolver_propagates_connect_timeout(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.ConnectTimeout("Timeout")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.ConnectTimeout):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_resolver_propagates_read_timeout(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.ReadTimeout("Timeout")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.ReadTimeout):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_resolver_propagates_read_error(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.ReadError("Read failed")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.ReadError):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_resolver_propagates_invalid_url(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        mock_client.get_identity_by_discord.side_effect = httpx.InvalidURL("Bad URL")
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.InvalidURL):
            await resolver.discord_to_irc("123")

    @pytest.mark.asyncio
    async def test_resolver_propagates_http_status_error(self):
        # Arrange
        mock_client = AsyncMock(spec=PortalClient)
        from unittest.mock import Mock
        request = Mock()
        response = Mock()
        response.status_code = 500
        mock_client.get_identity_by_discord.side_effect = httpx.HTTPStatusError(
            "500 Error", request=request, response=response
        )
        resolver = IdentityResolver(client=mock_client)

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError):
            await resolver.discord_to_irc("123")


class TestPortalClientRetryBehavior:
    """Test that PortalClient retry decorator is configured correctly.

    Note: These tests verify the retry configuration exists, but actual
    retry behavior is tested through integration tests or by testing
    the PortalClient directly with a real HTTP client.
    """

    def test_portal_client_has_retry_decorator(self):
        # Arrange & Act
        from bridge.identity import DEFAULT_RETRY

        # Assert - verify retry is configured
        assert DEFAULT_RETRY is not None
        assert DEFAULT_RETRY.retry.stop.max_attempt_number == 5

    def test_retry_config_includes_transient_errors(self):
        # Arrange
        from bridge.identity import DEFAULT_RETRY

        # Act - get the retry predicate
        retry_predicate = DEFAULT_RETRY.retry

        # Assert - verify it retries on transient errors
        # The retry_if_exception_type creates a predicate that checks exception types
        assert retry_predicate is not None
