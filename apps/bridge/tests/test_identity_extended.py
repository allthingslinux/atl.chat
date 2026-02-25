"""Additional identity resolver tests covering previously uncovered methods."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from bridge.identity import IdentityResolver, PortalClient


def make_resolver(return_value=None, *, method="get_identity_by_discord", ttl=3600):
    client = AsyncMock(spec=PortalClient)
    getattr(client, method).return_value = return_value
    return client, IdentityResolver(client=client, ttl=ttl)


# ---------------------------------------------------------------------------
# xmpp_to_* methods (previously 0% covered)
# ---------------------------------------------------------------------------


class TestXmppToMethods:
    @pytest.mark.asyncio
    async def test_xmpp_to_irc(self):
        # Arrange
        _, resolver = make_resolver({"irc_nick": "ircuser"}, method="get_identity_by_xmpp_jid")

        # Act
        result = await resolver.xmpp_to_irc("user@example.com")

        # Assert
        assert result == "ircuser"

    @pytest.mark.asyncio
    async def test_xmpp_to_irc_returns_none_when_not_linked(self):
        # Arrange
        _, resolver = make_resolver(None, method="get_identity_by_xmpp_jid")

        # Act
        result = await resolver.xmpp_to_irc("user@example.com")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_xmpp_to_discord(self):
        # Arrange
        _, resolver = make_resolver({"discord_id": "999"}, method="get_identity_by_xmpp_jid")

        # Act
        result = await resolver.xmpp_to_discord("user@example.com")

        # Assert
        assert result == "999"

    @pytest.mark.asyncio
    async def test_xmpp_to_discord_returns_none_when_not_linked(self):
        # Arrange
        _, resolver = make_resolver(None, method="get_identity_by_xmpp_jid")

        # Act
        result = await resolver.xmpp_to_discord("user@example.com")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_xmpp_to_portal_user(self):
        # Arrange
        _, resolver = make_resolver({"user_id": "portal-u-1"}, method="get_identity_by_xmpp_jid")

        # Act
        result = await resolver.xmpp_to_portal_user("user@example.com")

        # Assert
        assert result == "portal-u-1"

    @pytest.mark.asyncio
    async def test_xmpp_to_portal_user_returns_none_when_not_linked(self):
        # Arrange
        _, resolver = make_resolver(None, method="get_identity_by_xmpp_jid")

        # Act
        result = await resolver.xmpp_to_portal_user("user@example.com")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_xmpp_lookups_share_cache(self):
        """xmpp_to_irc and xmpp_to_discord for the same JID share the same cache entry."""
        # Arrange
        client, resolver = make_resolver(
            {"irc_nick": "ircnick", "discord_id": "555"},
            method="get_identity_by_xmpp_jid",
        )

        # Act — two lookups for the same JID
        await resolver.xmpp_to_irc("user@example.com")
        await resolver.xmpp_to_discord("user@example.com")

        # Assert — only one remote API call was made (second was cache hit)
        client.get_identity_by_xmpp_jid.assert_called_once()


# ---------------------------------------------------------------------------
# irc_to_portal_user (previously uncovered)
# ---------------------------------------------------------------------------


class TestIrcToPortalUser:
    @pytest.mark.asyncio
    async def test_irc_to_portal_user(self):
        # Arrange
        _, resolver = make_resolver({"user_id": "portal-u-2"}, method="get_identity_by_irc_nick")

        # Act
        result = await resolver.irc_to_portal_user("mynick")

        # Assert
        assert result == "portal-u-2"

    @pytest.mark.asyncio
    async def test_irc_to_portal_user_with_server(self):
        # Arrange
        client, resolver = make_resolver({"user_id": "portal-u-3"}, method="get_identity_by_irc_nick")

        # Act
        result = await resolver.irc_to_portal_user("mynick", "irc.libera.chat")

        # Assert
        assert result == "portal-u-3"
        client.get_identity_by_irc_nick.assert_called_once_with("mynick", server="irc.libera.chat")

    @pytest.mark.asyncio
    async def test_irc_to_portal_user_returns_none_when_not_found(self):
        # Arrange
        _, resolver = make_resolver(None, method="get_identity_by_irc_nick")

        # Act
        result = await resolver.irc_to_portal_user("ghost")

        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# discord_to_portal_user (previously uncovered)
# ---------------------------------------------------------------------------


class TestDiscordToPortalUser:
    @pytest.mark.asyncio
    async def test_discord_to_portal_user(self):
        # Arrange
        _, resolver = make_resolver({"user_id": "portal-u-4"})

        # Act
        result = await resolver.discord_to_portal_user("123")

        # Assert
        assert result == "portal-u-4"

    @pytest.mark.asyncio
    async def test_discord_to_portal_user_returns_none(self):
        # Arrange
        _, resolver = make_resolver(None)

        # Act
        result = await resolver.discord_to_portal_user("999")

        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# irc_to_xmpp (previously uncovered)
# ---------------------------------------------------------------------------


class TestIrcToXmpp:
    @pytest.mark.asyncio
    async def test_irc_to_xmpp(self):
        # Arrange
        _, resolver = make_resolver({"xmpp_jid": "nick@xmpp.example.com"}, method="get_identity_by_irc_nick")

        # Act
        result = await resolver.irc_to_xmpp("mynick")

        # Assert
        assert result == "nick@xmpp.example.com"

    @pytest.mark.asyncio
    async def test_irc_to_xmpp_returns_none_when_not_linked(self):
        # Arrange
        _, resolver = make_resolver(None, method="get_identity_by_irc_nick")

        # Act
        result = await resolver.irc_to_xmpp("ghost")

        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# has_xmpp (previously uncovered)
# ---------------------------------------------------------------------------


class TestHasXmppAdditional:
    @pytest.mark.asyncio
    async def test_has_xmpp_true(self):
        # Arrange
        _, resolver = make_resolver({"xmpp_jid": "user@xmpp.example.com"})

        # Act
        result = await resolver.has_xmpp("123")

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_has_xmpp_false_when_no_jid(self):
        # Arrange — identity exists but has no xmpp_jid key
        _, resolver = make_resolver({"discord_id": "123"})

        # Act
        result = await resolver.has_xmpp("123")

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_has_xmpp_false_when_no_identity(self):
        # Arrange — portal returns no identity at all
        _, resolver = make_resolver(None)

        # Act
        result = await resolver.has_xmpp("999")

        # Assert
        assert result is False


# ---------------------------------------------------------------------------
# PortalClient._extract raw dict passthrough
# ---------------------------------------------------------------------------


class TestPortalClientExtract:
    def test_extract_returns_none_for_string(self):
        # Arrange
        client = PortalClient("https://portal.example.com")

        # Act
        result = client._extract("not a dict")

        # Assert
        assert result is None

    def test_extract_returns_none_for_int(self):
        # Arrange
        client = PortalClient("https://portal.example.com")

        # Act
        result = client._extract(42)

        # Assert
        assert result is None

    def test_extract_returns_none_for_none(self):
        # Arrange
        client = PortalClient("https://portal.example.com")

        # Act
        result = client._extract(None)

        # Assert
        assert result is None

    def test_extract_returns_none_for_list(self):
        # Arrange
        client = PortalClient("https://portal.example.com")

        # Act
        result = client._extract(["list"])

        # Assert
        assert result is None

    def test_extract_wrapped_ok_true(self):
        # Arrange
        client = PortalClient("https://portal.example.com")
        payload = {"ok": True, "identity": {"irc_nick": "user"}}

        # Act
        result = client._extract(payload)

        # Assert
        assert result == {"irc_nick": "user"}

    def test_extract_wrapped_ok_false_returns_none(self):
        # Arrange
        client = PortalClient("https://portal.example.com")
        payload = {"ok": False, "identity": {"irc_nick": "user"}}

        # Act
        result = client._extract(payload)

        # Assert
        assert result is None

    def test_extract_raw_dict_passthrough(self):
        """Dict without 'ok' key is returned as-is."""
        # Arrange
        client = PortalClient("https://portal.example.com")
        raw = {"irc_nick": "user", "discord_id": "123"}

        # Act
        result = client._extract(raw)

        # Assert
        assert result == raw
