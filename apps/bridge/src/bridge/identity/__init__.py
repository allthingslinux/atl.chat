"""Identity resolution: Portal client and dev resolver (AUDIT §1)."""

from bridge.identity.base import IdentityResolver
from bridge.identity.dev import DevIdentityResolver
from bridge.identity.portal import DEFAULT_RETRY, PortalClient, PortalIdentityResolver
from bridge.identity.sanitize import ensure_valid_username, sanitize_nick

__all__ = [
    "DEFAULT_RETRY",
    "DevIdentityResolver",
    "IdentityResolver",
    "PortalClient",
    "PortalIdentityResolver",
    "ensure_valid_username",
    "sanitize_nick",
]
