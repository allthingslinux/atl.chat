"""Test identity resolver functionality."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import hypothesis
import hypothesis.strategies
import pytest
from bridge.identity import DevIdentityResolver, PortalClient, PortalIdentityResolver


def make_resolver(return_value=None, *, method="get_identity_by_discord", ttl=3600):
    """Create a resolver with a pre-configured mock client."""
    client = AsyncMock(spec=PortalClient)
    getattr(client, method).return_value = return_value
    return client, PortalIdentityResolver(client=client, ttl=ttl)


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
        client, resolver = make_resolver({"discord_id": "123", "irc_nick": "user", "xmpp_jid": "user@example.com"})
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
        client, resolver = make_resolver({"discord_id": "456"}, method="get_identity_by_irc_nick")
        assert await resolver.irc_to_discord("nick", "irc.libera.chat") == "456"
        client.get_identity_by_irc_nick.assert_called_once_with("nick", server="irc.libera.chat")

    @pytest.mark.asyncio
    async def test_irc_to_discord_cache_hit(self):
        client, resolver = make_resolver({"discord_id": "456"}, method="get_identity_by_irc_nick")
        await resolver.irc_to_discord("nick")
        await resolver.irc_to_discord("nick")
        client.get_identity_by_irc_nick.assert_called_once()


class TestXmppToDiscordCache:
    @pytest.mark.asyncio
    async def test_xmpp_to_discord_cache_hit(self):
        client, resolver = make_resolver({"discord_id": "789"}, method="get_identity_by_xmpp_jid")
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


class TestPortalClientLifecycle:
    """Test PortalClient shared httpx.AsyncClient lifecycle.

    Requirements: 1.1, 1.2, 1.3, 1.4, 1.6
    """

    @pytest.mark.asyncio
    async def test_aopen_creates_client(self):
        portal = PortalClient("http://portal", token="t")
        assert portal._client is None
        await portal.aopen()
        try:
            assert portal._client is not None
            assert isinstance(portal._client, httpx.AsyncClient)
        finally:
            await portal.aclose()

    @pytest.mark.asyncio
    async def test_aclose_closes_and_nils_client(self):
        portal = PortalClient("http://portal", token="t")
        await portal.aopen()
        assert portal._client is not None
        await portal.aclose()
        assert portal._client is None

    @pytest.mark.asyncio
    async def test_aclose_is_idempotent(self):
        portal = PortalClient("http://portal", token="t")
        await portal.aopen()
        await portal.aclose()
        await portal.aclose()  # should not raise
        assert portal._client is None

    @pytest.mark.asyncio
    async def test_request_raises_before_aopen(self):
        portal = PortalClient("http://portal", token="t")
        with pytest.raises(AssertionError, match="call aopen"):
            await portal._request({"discordId": "123"})

    @pytest.mark.asyncio
    async def test_get_identity_methods_reuse_same_client(self):
        """All get_identity_by_* calls use the same httpx.AsyncClient instance."""
        portal = PortalClient("http://portal", token="t")
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"irc_nick": "user"}
        resp.raise_for_status.return_value = None

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=resp)
        mock_http.aclose = AsyncMock()
        portal._client = mock_http

        client_before = portal._client
        await portal.get_identity_by_discord("123")
        assert portal._client is client_before
        await portal.get_identity_by_irc_nick("nick")
        assert portal._client is client_before
        await portal.get_identity_by_xmpp_jid("user@example.com")
        assert portal._client is client_before

    @pytest.mark.asyncio
    async def test_async_context_manager_opens_and_closes(self):
        async with PortalClient("http://portal", token="t") as portal:
            assert portal._client is not None
            assert isinstance(portal._client, httpx.AsyncClient)
        assert portal._client is None

    @pytest.mark.asyncio
    async def test_async_context_manager_closes_on_exception(self):
        portal = PortalClient("http://portal", token="t")
        with pytest.raises(RuntimeError):
            async with portal:
                assert portal._client is not None
                raise RuntimeError("boom")
        assert portal._client is None


# ---------------------------------------------------------------------------
# PortalClient direct HTTP behaviour
# ---------------------------------------------------------------------------


class TestPortalClient:
    """Test PortalClient 404 / error / non-dict responses."""

    def _mock_response(self, status_code: int, json_data=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data
        if status_code >= 400:
            resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
        else:
            resp.raise_for_status.return_value = None
        return resp

    async def _make_client(self, resp):
        """Create a PortalClient with aopen() and a mocked shared httpx client."""
        client = PortalClient(base_url="http://portal", token="t")
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=resp)
        mock_http.aclose = AsyncMock()
        client._client = mock_http
        return client, mock_http

    @pytest.mark.asyncio
    async def test_get_by_discord_404_returns_none(self):
        resp = self._mock_response(404)
        client, _ = await self._make_client(resp)
        result = await client.get_identity_by_discord("u1")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_discord_non_dict_returns_none(self):
        resp = self._mock_response(200, json_data=["list", "not", "dict"])
        client, _ = await self._make_client(resp)
        result = await client.get_identity_by_discord("u1")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_discord_dict_returns_data(self):
        resp = self._mock_response(200, json_data={"discord_id": "u1", "irc_nick": "user"})
        client, _ = await self._make_client(resp)
        result = await client.get_identity_by_discord("u1")
        assert result == {"discord_id": "u1", "irc_nick": "user"}

    @pytest.mark.asyncio
    async def test_get_by_irc_nick_404_returns_none(self):
        resp = self._mock_response(404)
        client, _ = await self._make_client(resp)
        result = await client.get_identity_by_irc_nick("nick")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_irc_nick_non_dict_returns_none(self):
        resp = self._mock_response(200, json_data=42)
        client, _ = await self._make_client(resp)
        result = await client.get_identity_by_irc_nick("nick")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_irc_nick_with_server_passes_param(self):
        resp = self._mock_response(200, json_data={"irc_nick": "nick"})
        client, mock_http = await self._make_client(resp)
        await client.get_identity_by_irc_nick("nick", server="irc.libera.chat")
        _, kwargs = mock_http.get.call_args
        assert kwargs["params"]["ircServer"] == "irc.libera.chat"

    @pytest.mark.asyncio
    async def test_get_by_xmpp_jid_404_returns_none(self):
        resp = self._mock_response(404)
        client, _ = await self._make_client(resp)
        result = await client.get_identity_by_xmpp_jid("user@xmpp.example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_xmpp_jid_non_dict_returns_none(self):
        resp = self._mock_response(200, json_data=None)
        client, _ = await self._make_client(resp)
        result = await client.get_identity_by_xmpp_jid("user@xmpp.example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_xmpp_jid_dict_returns_data(self):
        resp = self._mock_response(200, json_data={"xmpp_jid": "user@xmpp.example.com"})
        client, _ = await self._make_client(resp)
        result = await client.get_identity_by_xmpp_jid("user@xmpp.example.com")
        assert result == {"xmpp_jid": "user@xmpp.example.com"}


class TestDevIdentityResolver:
    """Test DevIdentityResolver for IRC puppets without Portal."""

    @pytest.mark.asyncio
    async def test_discord_to_irc_fallback_nick(self):
        with patch.dict(os.environ, {"BRIDGE_DEV_IRC_NICK_MAP": ""}, clear=False):
            resolver = DevIdentityResolver()
        assert await resolver.discord_to_irc("123456789012345678") == "atl_dev_12345678"
        assert await resolver.discord_to_irc("123") == "atl_dev_123"

    @pytest.mark.asyncio
    async def test_discord_to_irc_from_nick_map(self):
        with patch.dict(
            os.environ,
            {"BRIDGE_DEV_IRC_NICK_MAP": "123456789012345678:atl-o,987654321098765432:atl-user"},
            clear=False,
        ):
            resolver = DevIdentityResolver()
        assert await resolver.discord_to_irc("123456789012345678") == "atl-o"
        assert await resolver.discord_to_irc("987654321098765432") == "atl-user"
        assert await resolver.discord_to_irc("111111111111111111") == "atl_dev_11111111"

    @pytest.mark.asyncio
    async def test_has_irc_always_true(self):
        with patch.dict(os.environ, {}, clear=False):
            resolver = DevIdentityResolver()
        assert await resolver.has_irc("any") is True

    @pytest.mark.asyncio
    async def test_irc_to_discord_from_nick_map(self):
        with patch.dict(
            os.environ,
            {"BRIDGE_DEV_IRC_NICK_MAP": "123456789012345678:atl-o"},
            clear=False,
        ):
            resolver = DevIdentityResolver()
        assert await resolver.irc_to_discord("atl-o") == "123456789012345678"
        assert await resolver.irc_to_discord("unknown") is None

    @pytest.mark.asyncio
    async def test_discord_to_xmpp_returns_none(self):
        with patch.dict(os.environ, {}, clear=False):
            resolver = DevIdentityResolver()
        assert await resolver.discord_to_xmpp("any") is None

    @pytest.mark.asyncio
    async def test_has_xmpp_returns_false(self):
        with patch.dict(os.environ, {}, clear=False):
            resolver = DevIdentityResolver()
        assert await resolver.has_xmpp("any") is False


class TestDevIdentityResolverABC:
    """Test DevIdentityResolver extends IdentityResolver ABC and supports programmatic mappings."""

    def test_is_instance_of_identity_resolver_abc(self):
        from bridge.identity.base import IdentityResolver as IdentityResolverABC

        with patch.dict(os.environ, {}, clear=False):
            resolver = DevIdentityResolver()
        assert isinstance(resolver, IdentityResolverABC)

    @pytest.mark.asyncio
    async def test_add_discord_irc_mapping(self):
        with patch.dict(os.environ, {}, clear=False):
            resolver = DevIdentityResolver()
        resolver.add_discord_irc_mapping("111", "testuser")
        assert await resolver.discord_to_irc("111") == "testuser"
        assert await resolver.irc_to_discord("testuser") == "111"

    @pytest.mark.asyncio
    async def test_add_discord_xmpp_mapping(self):
        with patch.dict(os.environ, {}, clear=False):
            resolver = DevIdentityResolver()
        resolver.add_discord_xmpp_mapping("222", "user@xmpp.example.com")
        assert await resolver.discord_to_xmpp("222") == "user@xmpp.example.com"
        assert await resolver.xmpp_to_discord("user@xmpp.example.com") == "222"
        assert await resolver.has_xmpp("222") is True
        assert await resolver.has_xmpp("999") is False

    @pytest.mark.asyncio
    async def test_add_irc_xmpp_mapping(self):
        with patch.dict(os.environ, {}, clear=False):
            resolver = DevIdentityResolver()
        resolver.add_irc_xmpp_mapping("ircnick", "nick@xmpp.example.com")
        assert await resolver.irc_to_xmpp("ircnick") == "nick@xmpp.example.com"
        assert await resolver.xmpp_to_irc("nick@xmpp.example.com") == "ircnick"

    @pytest.mark.asyncio
    async def test_add_portal_mappings(self):
        with patch.dict(os.environ, {}, clear=False):
            resolver = DevIdentityResolver()
        resolver.add_discord_portal_mapping("111", "portal-1")
        resolver.add_irc_portal_mapping("nick", "portal-2")
        resolver.add_xmpp_portal_mapping("user@xmpp.example.com", "portal-3")
        assert await resolver.discord_to_portal_user("111") == "portal-1"
        assert await resolver.irc_to_portal_user("nick") == "portal-2"
        assert await resolver.xmpp_to_portal_user("user@xmpp.example.com") == "portal-3"

    @pytest.mark.asyncio
    async def test_unmapped_lookups_return_none(self):
        with patch.dict(os.environ, {}, clear=False):
            resolver = DevIdentityResolver()
        assert await resolver.discord_to_xmpp("unknown") is None
        assert await resolver.irc_to_xmpp("unknown") is None
        assert await resolver.xmpp_to_discord("unknown") is None
        assert await resolver.xmpp_to_irc("unknown") is None
        assert await resolver.discord_to_portal_user("unknown") is None
        assert await resolver.irc_to_portal_user("unknown") is None
        assert await resolver.xmpp_to_portal_user("unknown") is None


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------


class TestPortalClientSharedInstanceProperty:
    """Property 2: PortalClient shared instance reuse.

    For any sequence of get_identity_by_* calls after aopen(), all calls
    use the same httpx.AsyncClient instance.

    **Validates: Requirements 1.2**
    """

    METHOD_CHOICES = [
        ("get_identity_by_discord", {"discord_id": "123"}),
        ("get_identity_by_irc_nick", {"nick": "user"}),
        ("get_identity_by_irc_nick", {"nick": "user", "server": "irc.example.com"}),
        ("get_identity_by_xmpp_jid", {"jid": "user@example.com"}),
    ]

    @pytest.mark.asyncio
    @hypothesis.given(
        call_indices=hypothesis.strategies.lists(
            hypothesis.strategies.sampled_from(range(4)),
            min_size=1,
            max_size=20,
        )
    )
    async def test_all_calls_reuse_same_client(self, call_indices: list[int]) -> None:
        """Any sequence of get_identity_by_* calls shares one httpx.AsyncClient."""
        portal = PortalClient("http://portal", token="t")

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"ok": True, "identity": {"irc_nick": "u"}}
        resp.raise_for_status.return_value = None

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=resp)
        mock_http.aclose = AsyncMock()
        portal._client = mock_http

        original_client = portal._client

        for idx in call_indices:
            method_name, kwargs = self.METHOD_CHOICES[idx]
            await getattr(portal, method_name)(**kwargs)
            assert portal._client is original_client, f"Client changed after {method_name}() call"
