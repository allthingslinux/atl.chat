"""Portal identity client + TTL cache (AUDIT §1)."""

from __future__ import annotations

from typing import Any

import httpx
from cachetools import TTLCache
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

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
            httpx.HTTPStatusError,
        )
    ),
    reraise=True,
)


class PortalClient:
    """Async client for Portal Bridge API. Uses tenacity for retries."""

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

    def _extract(self, data: Any) -> dict[str, Any] | None:
        if not isinstance(data, dict):
            return None
        if "ok" in data:
            return data.get("identity") if data.get("ok") else None
        return data

    @DEFAULT_RETRY
    async def get_identity_by_discord(self, discord_id: str) -> dict[str, Any] | None:
        url = f"{self._base_url}/api/bridge/identity"
        params = {"discordId": discord_id}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params, headers=self._headers())
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return self._extract(resp.json())

    @DEFAULT_RETRY
    async def get_identity_by_irc_nick(
        self,
        nick: str,
        *,
        server: str | None = None,
    ) -> dict[str, Any] | None:
        url = f"{self._base_url}/api/bridge/identity"
        params: dict[str, str] = {"ircNick": nick}
        if server:
            params["ircServer"] = server
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params, headers=self._headers())
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return self._extract(resp.json())

    @DEFAULT_RETRY
    async def get_identity_by_xmpp_jid(self, jid: str) -> dict[str, Any] | None:
        url = f"{self._base_url}/api/bridge/identity"
        params = {"xmppJid": jid}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params, headers=self._headers())
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return self._extract(resp.json())


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

    async def _get_discord(self, discord_id: str) -> dict[str, Any] | None:
        key = self._cache_key("discord", discord_id)
        try:
            return self._cache[key]
        except KeyError:
            logger.debug("Identity cache miss: discord_id={}", discord_id)
            data = await self._client.get_identity_by_discord(discord_id)
            self._cache[key] = data
            return data

    async def _get_irc(self, nick: str, server: str | None) -> dict[str, Any] | None:
        key = self._cache_key("irc", nick, server or "")
        try:
            return self._cache[key]
        except KeyError:
            logger.debug("Identity cache miss: irc nick={} server={}", nick, server)
            data = await self._client.get_identity_by_irc_nick(nick, server=server)
            self._cache[key] = data
            return data

    async def _get_xmpp(self, jid: str) -> dict[str, Any] | None:
        key = self._cache_key("xmpp", jid)
        try:
            return self._cache[key]
        except KeyError:
            logger.debug("Identity cache miss: xmpp jid={}", jid)
            data = await self._client.get_identity_by_xmpp_jid(jid)
            self._cache[key] = data
            return data

    async def discord_to_irc(self, discord_id: str) -> str | None:
        data = await self._get_discord(discord_id)
        return data.get("irc_nick") if data else None

    async def discord_to_xmpp(self, discord_id: str) -> str | None:
        data = await self._get_discord(discord_id)
        return data.get("xmpp_jid") if data else None

    async def discord_to_portal_user(self, discord_id: str) -> str | None:
        data = await self._get_discord(discord_id)
        return data.get("user_id") if data else None

    async def irc_to_xmpp(self, nick: str, server: str | None = None) -> str | None:
        data = await self._get_irc(nick, server)
        return data.get("xmpp_jid") if data else None

    async def irc_to_discord(self, nick: str, server: str | None = None) -> str | None:
        data = await self._get_irc(nick, server)
        return data.get("discord_id") if data else None

    async def irc_to_portal_user(self, nick: str, server: str | None = None) -> str | None:
        data = await self._get_irc(nick, server)
        return data.get("user_id") if data else None

    async def xmpp_to_irc(self, jid: str) -> str | None:
        data = await self._get_xmpp(jid)
        return data.get("irc_nick") if data else None

    async def xmpp_to_discord(self, jid: str) -> str | None:
        data = await self._get_xmpp(jid)
        return data.get("discord_id") if data else None

    async def xmpp_to_portal_user(self, jid: str) -> str | None:
        data = await self._get_xmpp(jid)
        return data.get("user_id") if data else None

    async def has_irc(self, discord_id: str) -> bool:
        nick = await self.discord_to_irc(discord_id)
        return nick is not None

    async def has_xmpp(self, discord_id: str) -> bool:
        jid = await self.discord_to_xmpp(discord_id)
        return jid is not None
