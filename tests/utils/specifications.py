"""IRC specification definitions and test markers.

Adapted from irctest's specifications module for marking tests by IRC specification.
"""

from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

import pytest


class Specification(Enum):
    """IRC protocol specifications."""

    RFC1459 = "RFC1459"
    RFC2812 = "RFC2812"
    IRCv3 = "IRCv3"
    Modern = "modern"
    IRCdocs = "ircdocs"
    Ergo = "Ergo"

    @classmethod
    def from_name(cls, name: str) -> "Specification":
        """Get specification from string name."""
        try:
            return cls[name.upper()]
        except KeyError:
            raise ValueError(f"Unknown specification: {name}")


class Capability(Enum):
    """IRCv3 capabilities."""

    ACCOUNT_NOTIFY = "account-notify"
    ACCOUNT_TAG = "account-tag"
    AWAY_NOTIFY = "away-notify"
    BATCH = "batch"
    ECHO_MESSAGE = "echo-message"
    EXTENDED_JOIN = "extended-join"
    EXTENDED_MONITOR = "extended-monitor"
    LABELED_RESPONSE = "labeled-response"
    MESSAGE_TAGS = "message-tags"
    METADATA_2 = "metadata-2"
    MULTILINE = "draft/multiline"
    MULTI_PREFIX = "multi-prefix"
    SERVER_TIME = "server-time"
    SETNAME = "setname"
    STS = "sts"

    @classmethod
    def from_name(cls, name: str) -> "Capability":
        """Get capability from string name."""
        # Handle special cases
        name = name.replace("-", "_").replace("/", "_").upper()
        try:
            return cls[name]
        except KeyError:
            raise ValueError(f"Unknown capability: {name}")


class ISupportToken(Enum):
    """ISUPPORT tokens."""

    BOT = "BOT"
    ELIST = "ELIST"
    INVEX = "INVEX"
    MONITOR = "MONITOR"
    PREFIX = "PREFIX"
    STATUSMSG = "STATUSMSG"
    TARGMAX = "TARGMAX"
    UTF8ONLY = "UTF8ONLY"
    WHOX = "WHOX"

    @classmethod
    def from_name(cls, name: str) -> "ISupportToken":
        """Get ISUPPORT token from string name."""
        try:
            return cls[name.upper()]
        except KeyError:
            raise ValueError(f"Unknown ISUPPORT token: {name}")


TCallable = TypeVar("TCallable", bound=Callable)


def mark_specifications(
    *specifications_str: str, deprecated: bool = False, strict: bool = False
) -> Callable[[TCallable], TCallable]:
    """Mark a test function with IRC specifications."""
    specifications = frozenset(Specification.from_name(s) if isinstance(s, str) else s for s in specifications_str)
    if None in specifications:
        raise ValueError(f"Invalid set of specifications: {specifications}")

    def decorator(f: TCallable) -> TCallable:
        for specification in specifications:
            f = getattr(pytest.mark, specification.value)(f)
        if strict:
            f = pytest.mark.strict(f)
        if deprecated:
            f = pytest.mark.deprecated(f)
        return f

    return decorator


def mark_capabilities(
    *capabilities_str: str, deprecated: bool = False, strict: bool = False
) -> Callable[[TCallable], TCallable]:
    """Mark a test function with IRCv3 capabilities."""
    capabilities = frozenset(Capability.from_name(c) if isinstance(c, str) else c for c in capabilities_str)
    if None in capabilities:
        raise ValueError(f"Invalid set of capabilities: {capabilities}")

    def decorator(f: TCallable) -> TCallable:
        for capability in capabilities:
            f = getattr(pytest.mark, capability.value)(f)
        # Support for any capability implies IRCv3
        f = pytest.mark.IRCv3(f)
        return f

    return decorator


def mark_isupport(*tokens_str: str, deprecated: bool = False, strict: bool = False) -> Callable[[TCallable], TCallable]:
    """Mark a test function with ISUPPORT tokens."""
    tokens = frozenset(ISupportToken.from_name(c) if isinstance(c, str) else c for c in tokens_str)
    if None in tokens:
        raise ValueError(f"Invalid set of isupport tokens: {tokens}")

    def decorator(f: TCallable) -> TCallable:
        for token in tokens:
            f = getattr(pytest.mark, token.value)(f)
        return f

    return decorator


def mark_services(cls: Any) -> Any:
    """Mark a test class as requiring services."""
    cls.run_services = True
    return pytest.mark.services(cls)
