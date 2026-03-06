"""Portal identity client + TTL cache (AUDIT §1)."""

from __future__ import annotations

import time
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

from bridge.identity.base import IdentityResolver

DEFAULT_RETRY = retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
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

# ---------------------------------------------------------------------------
# Circuit breaker: skip requests when Portal is known to be unreachable
# ---------------------------------------------------------------------------
_CIRCUIT_FAIL_THRESHOLD = 3  # consecutive failures before opening
_CIRCUIT_COOLDOWN = 60.0  # seconds to wait before probing again


class PortalClient:
    """Async client for Portal Bridge API. Uses tenacity for retries.

    Maintains a shared ``httpx.AsyncClient`` with connection pooling.
    Call ``aopen()`` before use and ``aclose()`` on shutdown, or use as
    an async context manager::

        async with PortalClient(url, token=tok) as portal:
            await portal.get_identity_by_discord("123")
    """

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        # Circuit breaker state
        self._consecutive_failures: int = 0
        self._circuit_open_until: float = 0.0

    # -- lifecycle -----------------------------------------------------------

    async def aopen(self) -> None:
        """Create the shared ``httpx.AsyncClient`` with pool limits and transport retries."""
        transport = httpx.AsyncHTTPTransport(retries=1)
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            headers=self._headers(),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            transport=transport,
            http2=True,
        )

    async def aclose(self) -> None:
        """Close the shared client and release pooled connections."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> PortalClient:
        await self.aopen()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    # -- helpers -------------------------------------------------------------

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

    # -- unified request -----------------------------------------------------

    @DEFAULT_RETRY
    async def _request(self, params: dict[str, str]) -> dict[str, Any] | None:
        """Unified GET to ``/api/bridge/identity`` using the shared client.

        Includes a circuit breaker: after ``_CIRCUIT_FAIL_THRESHOLD`` consecutive
        connection failures, further requests are short-circuited for
        ``_CIRCUIT_COOLDOWN`` seconds to avoid blocking message delivery.
        """
        assert self._client is not None, "call aopen() first"

        # Circuit breaker: skip if Portal is known to be down
        now = time.monotonic()
        if self._consecutive_failures >= _CIRCUIT_FAIL_THRESHOLD:
            if now < self._circuit_open_until:
                return None
            # Cooldown expired — allow one probe request through
            logger.debug("Portal circuit breaker: probing after cooldown")

        url = f"{self._base_url}/api/bridge/identity"
        try:
            resp = await self._client.get(url, params=params)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            self._consecutive_failures += 1
            if self._consecutive_failures == _CIRCUIT_FAIL_THRESHOLD:
                self._circuit_open_until = time.monotonic() + _CIRCUIT_COOLDOWN
                logger.warning(
                    "Portal unreachable ({} consecutive failures); circuit breaker open for {}s",
                    self._consecutive_failures,
                    _CIRCUIT_COOLDOWN,
                )
            raise exc

        # Success or non-connection error — reset breaker
        self._consecutive_failures = 0
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return self._extract(resp.json())

    # -- public API (unchanged signatures) -----------------------------------

    async def get_identity_by_discord(self, discord_id: str) -> dict[str, Any] | None:
        return await self._request({"discordId": discord_id})

    async def get_identity_by_irc_nick(
        self,
        nick: str,
        *,
        server: str | None = None,
    ) -> dict[str, Any] | None:
        params: dict[str, str] = {"ircNick": nick}
        if server:
            params["ircServer"] = server
        return await self._request(params)

    async def get_identity_by_xmpp_jid(self, jid: str) -> dict[str, Any] | None:
        return await self._request({"xmppJid": jid})


class PortalIdentityResolver(IdentityResolver):
    """Portal-backed identity resolver with TTL cache. Wraps PortalClient.

    Extends the :class:`IdentityResolver` ABC and implements all abstract
    methods using the Portal API with circuit breaker and retry.
    """

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
