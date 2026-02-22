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
        _, resolver = make_resolver({"irc_nick": "ircuser"}, method="get_identity_by_xmpp_jid")
        assert await resolver.xmpp_to_irc("user@example.com") == "ircuser"

    @pytest.mark.asyncio
    async def test_xmpp_to_irc_returns_none_when_not_linked(self):
        _, resolver = make_resolver(None, method="get_identity_by_xmpp_jid")
        assert await resolver.xmpp_to_irc("user@example.com") is None

    @pytest.mark.asyncio
    async def test_xmpp_to_discord(self):
        _, resolver = make_resolver({"discord_id": "999"}, method="get_identity_by_xmpp_jid")
        assert await resolver.xmpp_to_discord("user@example.com") == "999"

    @pytest.mark.asyncio
    async def test_xmpp_to_discord_returns_none_when_not_linked(self):
        _, resolver = make_resolver(None, method="get_identity_by_xmpp_jid")
        assert await resolver.xmpp_to_discord("user@example.com") is None

    @pytest.mark.asyncio
    async def test_xmpp_to_portal_user(self):
        _, resolver = make_resolver({"user_id": "portal-u-1"}, method="get_identity_by_xmpp_jid")
        assert await resolver.xmpp_to_portal_user("user@example.com") == "portal-u-1"

    @pytest.mark.asyncio
    async def test_xmpp_to_portal_user_returns_none_when_not_linked(self):
        _, resolver = make_resolver(None, method="get_identity_by_xmpp_jid")
        assert await resolver.xmpp_to_portal_user("user@example.com") is None

    @pytest.mark.asyncio
    async def test_xmpp_lookups_share_cache(self):
        """xmpp_to_irc and xmpp_to_discord for the same JID share the same cache entry."""
        client, resolver = make_resolver(
            {"irc_nick": "ircnick", "discord_id": "555"},
            method="get_identity_by_xmpp_jid",
        )
        await resolver.xmpp_to_irc("user@example.com")
        await resolver.xmpp_to_discord("user@example.com")
        # Only one API call
        client.get_identity_by_xmpp_jid.assert_called_once()


# ---------------------------------------------------------------------------
# irc_to_portal_user (previously uncovered)
# ---------------------------------------------------------------------------


class TestIrcToPortalUser:
    @pytest.mark.asyncio
    async def test_irc_to_portal_user(self):
        _, resolver = make_resolver({"user_id": "portal-u-2"}, method="get_identity_by_irc_nick")
        assert await resolver.irc_to_portal_user("mynick") == "portal-u-2"

    @pytest.mark.asyncio
    async def test_irc_to_portal_user_with_server(self):
        client, resolver = make_resolver(
            {"user_id": "portal-u-3"}, method="get_identity_by_irc_nick"
        )
        result = await resolver.irc_to_portal_user("mynick", "irc.libera.chat")
        assert result == "portal-u-3"
        client.get_identity_by_irc_nick.assert_called_once_with("mynick", server="irc.libera.chat")

    @pytest.mark.asyncio
    async def test_irc_to_portal_user_returns_none_when_not_found(self):
        _, resolver = make_resolver(None, method="get_identity_by_irc_nick")
        assert await resolver.irc_to_portal_user("ghost") is None


# ---------------------------------------------------------------------------
# discord_to_portal_user (previously uncovered)
# ---------------------------------------------------------------------------


class TestDiscordToPortalUser:
    @pytest.mark.asyncio
    async def test_discord_to_portal_user(self):
        _, resolver = make_resolver({"user_id": "portal-u-4"})
        assert await resolver.discord_to_portal_user("123") == "portal-u-4"

    @pytest.mark.asyncio
    async def test_discord_to_portal_user_returns_none(self):
        _, resolver = make_resolver(None)
        assert await resolver.discord_to_portal_user("999") is None


# ---------------------------------------------------------------------------
# irc_to_xmpp (previously uncovered)
# ---------------------------------------------------------------------------


class TestIrcToXmpp:
    @pytest.mark.asyncio
    async def test_irc_to_xmpp(self):
        _, resolver = make_resolver(
            {"xmpp_jid": "nick@xmpp.example.com"}, method="get_identity_by_irc_nick"
        )
        assert await resolver.irc_to_xmpp("mynick") == "nick@xmpp.example.com"

    @pytest.mark.asyncio
    async def test_irc_to_xmpp_returns_none_when_not_linked(self):
        _, resolver = make_resolver(None, method="get_identity_by_irc_nick")
        assert await resolver.irc_to_xmpp("ghost") is None


# ---------------------------------------------------------------------------
# has_xmpp (previously uncovered)
# ---------------------------------------------------------------------------


class TestHasXmppAdditional:
    @pytest.mark.asyncio
    async def test_has_xmpp_true(self):
        _, resolver = make_resolver({"xmpp_jid": "user@xmpp.example.com"})
        assert await resolver.has_xmpp("123") is True

    @pytest.mark.asyncio
    async def test_has_xmpp_false_when_no_jid(self):
        _, resolver = make_resolver({"discord_id": "123"})  # no xmpp_jid key
        assert await resolver.has_xmpp("123") is False

    @pytest.mark.asyncio
    async def test_has_xmpp_false_when_no_identity(self):
        _, resolver = make_resolver(None)
        assert await resolver.has_xmpp("999") is False


# ---------------------------------------------------------------------------
# PortalClient._extract raw dict passthrough
# ---------------------------------------------------------------------------


class TestPortalClientExtract:
    def test_extract_returns_none_for_non_dict(self):
        client = PortalClient("https://portal.example.com")
        assert client._extract("not a dict") is None
        assert client._extract(42) is None
        assert client._extract(None) is None
        assert client._extract(["list"]) is None

    def test_extract_wrapped_ok_true(self):
        client = PortalClient("https://portal.example.com")
        payload = {"ok": True, "identity": {"irc_nick": "user"}}
        assert client._extract(payload) == {"irc_nick": "user"}

    def test_extract_wrapped_ok_false_returns_none(self):
        client = PortalClient("https://portal.example.com")
        payload = {"ok": False, "identity": {"irc_nick": "user"}}
        assert client._extract(payload) is None

    def test_extract_raw_dict_passthrough(self):
        """Dict without 'ok' key is returned as-is."""
        client = PortalClient("https://portal.example.com")
        raw = {"irc_nick": "user", "discord_id": "123"}
        assert client._extract(raw) == raw
