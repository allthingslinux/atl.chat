"""Shared XMPP avatar URL resolution (PEP + vCard fallback)."""

from __future__ import annotations

import httpx
from cachetools import TTLCache

from bridge.config import cfg

_avatar_url_cache: TTLCache[tuple[str, str], str | None] = TTLCache(maxsize=500, ttl=86400)


def _get_cache() -> TTLCache[tuple[str, str], str | None]:
    """Return the module-level avatar URL cache (lazy TTL refresh from config)."""
    global _avatar_url_cache  # noqa: PLW0603
    if _avatar_url_cache.ttl != cfg.avatar_cache_ttl_seconds:
        _avatar_url_cache = TTLCache(maxsize=500, ttl=cfg.avatar_cache_ttl_seconds)
    return _avatar_url_cache


def resolve_xmpp_avatar_url(base_domain: str, node: str) -> str | None:
    """Resolve avatar URL: probe internally, return public URL for external consumers.

    The bridge probes Prosody via the internal ``xmpp_avatar_base_url`` (Docker hostname),
    but returns the ``xmpp_avatar_public_url`` so Discord (and other external services)
    can actually fetch the image. Falls back to ``https://{base_domain}`` when no
    explicit config is set.

    Args:
        base_domain: XMPP domain (e.g. "atl.chat"), derived from MUC JID.
        node: JID localpart (e.g. "alice").

    Returns:
        Public avatar URL or None.
    """
    cache = _get_cache()
    cache_key = (base_domain, node)
    if cache_key in cache:
        return cache[cache_key]

    # Build internal probe URLs (Docker-reachable)
    probe_base = cfg.xmpp_avatar_base_url
    probe_base = probe_base.rstrip("/") if probe_base else f"https://{base_domain}"

    # Build public URLs (what we return for Discord to fetch)
    public_base = cfg.xmpp_avatar_public_url
    public_base = public_base.rstrip("/") if public_base else f"https://{base_domain}"

    for path in (f"/pep_avatar/{node}", f"/avatar/{node}"):
        probe_url = f"{probe_base}{path}"
        try:
            r = httpx.head(probe_url, follow_redirects=True, timeout=1.5)
            if r.status_code == 200:
                public_url = f"{public_base}{path}"
                cache[cache_key] = public_url
                return public_url
        except Exception:
            continue

    cache[cache_key] = None
    return None


def xmpp_domain_from_muc_jid(muc_jid: str) -> str:
    """Extract base XMPP domain from a MUC JID (e.g. 'muc.atl.chat' -> 'atl.chat')."""
    domain = muc_jid.rsplit("@", maxsplit=1)[-1] if "@" in muc_jid else muc_jid
    # Strip resource
    domain = domain.split("/")[0]
    return domain[4:] if domain.startswith("muc.") else domain
