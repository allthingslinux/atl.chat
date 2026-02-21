"""Portal identity client + TTL cache (AUDIT §1: Portal is source of truth)."""

from __future__ import annotations

from typing import Any

import httpx
from cachetools import TTLCache
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Default retry: 5 attempts, exponential backoff 2–30s, retry on transient errors
DEFAULT_RETRY = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(
        (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
            httpx.ReadError,
            httpx.WriteError,
            httpx.HTTPStatusError,  # Will retry 5xx errors
        )
    ),
    reraise=True,
)


class PortalClient:
    """Async client for Portal Bridge API. Uses tenacity for retries.

    Portal identity endpoint: GET /api/bridge/identity
    Query params (exactly one required):
      - ircNick + optional ircServer  → identity keyed by IRC nick
      - xmppJid                       → identity keyed by XMPP JID

    Response shape (ok=True):
      IRC lookup:  { userId, nick, server, ircStatus, xmppJid, xmppUsername }
      XMPP lookup: { userId, jid, username, xmppStatus, ircNick, ircServer }
    """

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Accept": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    @DEFAULT_RETRY
    async def get_identity_by_discord(self, discord_id: str) -> dict[str, Any] | None:
        """Resolve Discord snowflake → userId, IRC nick, XMPP JID. Returns None if not found."""
        url = f"{self._base_url}/api/bridge/identity"
        params = {"discordId": discord_id}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params, headers=self._headers())
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and data.get("ok"):
                return data.get("identity")
            return None

    @DEFAULT_RETRY
    async def get_identity_by_irc_nick(
        self,
        nick: str,
        *,
        server: str | None = None,
    ) -> dict[str, Any] | None:
        """Resolve IRC nick → userId, XMPP JID. Returns None if not found."""
        url = f"{self._base_url}/api/bridge/identity"
        params: dict[str, str] = {"ircNick": nick}
        if server:
            params["ircServer"] = server
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params, headers=self._headers())
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and data.get("ok"):
                return data.get("identity")
            return None

    @DEFAULT_RETRY
    async def get_identity_by_xmpp_jid(self, jid: str) -> dict[str, Any] | None:
        """Resolve XMPP JID → userId, IRC nick. Returns None if not found."""
        url = f"{self._base_url}/api/bridge/identity"
        params = {"xmppJid": jid}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params, headers=self._headers())
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and data.get("ok"):
                return data.get("identity")
            return None


class IdentityResolver:
    """Identity resolver with TTL cache. Wraps PortalClient."""

    def __init__(
        self,
        client: PortalClient,
        *,
        maxsize: int = 1024,
        ttl: int = 3600,
    ) -> None:
        self._client = client
        self._cache: TTLCache[tuple[str, str], dict[str, Any] | None] = TTLCache(
            maxsize=maxsize,
            ttl=float(ttl),
        )
        self._ttl = ttl

    def _cache_key(self, lookup_type: str, value: str, extra: str = "") -> tuple[str, str]:
        return (lookup_type, f"{value}:{extra}")

    async def discord_to_irc(self, discord_id: str) -> str | None:
        """Get IRC nick for Discord user. Returns None if not linked."""
        key = self._cache_key("discord", discord_id)
        if key in self._cache:
            data = self._cache[key]
            return data.get("nick") if data else None
        data = await self._client.get_identity_by_discord(discord_id)
        self._cache[key] = data
        return data.get("nick") if data else None

    async def discord_to_xmpp(self, discord_id: str) -> str | None:
        """Get XMPP JID for Discord user. Returns None if not linked."""
        key = self._cache_key("discord", discord_id)
        if key in self._cache:
            data = self._cache[key]
            return data.get("jid") if data else None
        data = await self._client.get_identity_by_discord(discord_id)
        self._cache[key] = data
        return data.get("jid") if data else None

    async def discord_to_portal_user(self, discord_id: str) -> str | None:
        """Get Portal userId for Discord user. Returns None if not linked."""
        key = self._cache_key("discord", discord_id)
        if key in self._cache:
            data = self._cache[key]
            return data.get("userId") if data else None
        data = await self._client.get_identity_by_discord(discord_id)
        self._cache[key] = data
        return data.get("userId") if data else None

    async def irc_to_xmpp(self, nick: str, server: str | None = None) -> str | None:
        """Get XMPP JID for IRC nick. Returns None if not linked."""
        key = self._cache_key("irc", nick, server or "")
        if key in self._cache:
            data = self._cache[key]
            return data.get("xmppJid") if data else None
        data = await self._client.get_identity_by_irc_nick(nick, server=server)
        self._cache[key] = data
        return data.get("xmppJid") if data else None

    async def irc_to_portal_user(self, nick: str, server: str | None = None) -> str | None:
        """Get Portal userId for IRC nick. Returns None if not linked."""
        key = self._cache_key("irc", nick, server or "")
        if key in self._cache:
            data = self._cache[key]
            return data.get("userId") if data else None
        data = await self._client.get_identity_by_irc_nick(nick, server=server)
        self._cache[key] = data
        return data.get("userId") if data else None

    async def xmpp_to_irc(self, jid: str) -> str | None:
        """Get IRC nick for XMPP JID. Returns None if not linked."""
        key = self._cache_key("xmpp", jid)
        if key in self._cache:
            data = self._cache[key]
            return data.get("ircNick") if data else None
        data = await self._client.get_identity_by_xmpp_jid(jid)
        self._cache[key] = data
        return data.get("ircNick") if data else None

    async def xmpp_to_portal_user(self, jid: str) -> str | None:
        """Get Portal userId for XMPP JID. Returns None if not linked."""
        key = self._cache_key("xmpp", jid)
        if key in self._cache:
            data = self._cache[key]
            return data.get("userId") if data else None
        data = await self._client.get_identity_by_xmpp_jid(jid)
        self._cache[key] = data
        return data.get("userId") if data else None

    async def has_xmpp(self, irc_nick: str, server: str | None = None) -> bool:
        """Check if IRC nick has a linked XMPP account in Portal."""
        jid = await self.irc_to_xmpp(irc_nick, server=server)
        return jid is not None

    async def has_irc(self, xmpp_jid: str) -> bool:
        """Check if XMPP JID has a linked IRC account in Portal."""
        nick = await self.xmpp_to_irc(xmpp_jid)
        return nick is not None
