"""Webhook username and IRC/XMPP nick sanitization (Requirements 14.1, 14.2, 14.3).

``ensure_valid_username`` produces a Discord-safe webhook username (2–32 chars).
``sanitize_nick`` produces a nick safe for both IRC and XMPP MUC contexts.
"""

from __future__ import annotations

import os
import re

# ---------------------------------------------------------------------------
# Discord webhook username limits
# ---------------------------------------------------------------------------
_MIN_USERNAME_LEN = 2
_MAX_USERNAME_LEN = 32
_DEFAULT_USERNAME = "Bridge User"

# ---------------------------------------------------------------------------
# Nick forbidden / start character sets (from modern.ircdocs.horse, RFC 2812,
# UnrealIRCd, and Prosody mod_muc_limits)
# ---------------------------------------------------------------------------

# Characters that MUST NOT appear anywhere in a sanitized nick.
_FORBIDDEN_NICK_CHARS = frozenset(" ,*?!@#:/\\.\x00\r\n")

# Characters that MUST NOT appear at the start of a sanitized nick.
# Digits, slash, dash, single-quote, colon, hash, ampersand, at-sign,
# percent, plus, tilde, dollar.
_FORBIDDEN_START_CHARS = frozenset("0123456789/-':&#@%+~$")

_FORBIDDEN_NICK_RE = re.compile("[" + re.escape("".join(_FORBIDDEN_NICK_CHARS)) + "]")

_DEFAULT_NICK = "user"


def ensure_valid_username(name: str) -> str:
    """Produce a Discord webhook username with length in [2, 32].

    1. Strip leading/trailing whitespace.
    2. Truncate to 32 characters.
    3. If the result is shorter than 2 characters, use a default fallback.

    **Validates: Requirement 14.1**
    """
    name = str(name).strip()
    if len(name) < _MIN_USERNAME_LEN:
        name = _DEFAULT_USERNAME
    return name[:_MAX_USERNAME_LEN]


def sanitize_nick(nick: str, max_len: int = 23) -> str:
    """Produce a nick safe for IRC and XMPP MUC contexts.

    1. Remove all forbidden characters (space, comma, asterisk, question mark,
       exclamation mark, at-sign, hash, colon, slash, backslash, dot, NUL,
       CR, LF).
    2. Strip forbidden start characters (digit, slash, dash, single-quote,
       colon, hash, ampersand, at-sign, percent, plus, tilde, dollar).
    3. Truncate to *max_len* (default 23, the Prosody ``muc_max_nick_length``).
    4. If the result is empty, return a fallback (``"user"``).

    **Validates: Requirements 14.2, 14.3**
    """
    # Step 1: remove forbidden characters
    cleaned = _FORBIDDEN_NICK_RE.sub("", nick)

    # Step 2: strip forbidden start characters
    while cleaned and cleaned[0] in _FORBIDDEN_START_CHARS:
        cleaned = cleaned[1:]

    # Step 3: truncate
    cleaned = cleaned[:max_len]

    # Step 4: fallback
    if not cleaned:
        cleaned = _DEFAULT_NICK

    return cleaned


def xmpp_jid_or_plain_to_muc_nick(value: str, *, max_len: int = 23) -> str:
    """Turn Portal ``xmpp_jid`` or a plain display string into a MUC occupant nick.

    ``discord_to_xmpp`` returns a bare JID (e.g. ``alice@chat.example``). Using that
    full string as the MUC nick breaks join and echo matching: the server applies
    its own escaping for the resource, so ``mucnick`` may not match what we store
    in ``_recent_sent_nicks``. We always use the JID's local part, then
    :func:`sanitize_nick`.
    """
    value = str(value).strip()
    if not value:
        return sanitize_nick("", max_len=max_len)
    if "@" in value:
        local_part = value.split("@", 1)[0]
        if local_part:
            return sanitize_nick(local_part, max_len=max_len)
    return sanitize_nick(value, max_len=max_len)


def puppet_muc_nick_from_base(sanitized_nick: str, *, max_len: int = 23) -> str:
    """Append optional suffix to the MUC occupant nick (e.g. ``_bridge``).

    XEP-0045 requires nick uniqueness per room; two occupants cannot share the
    same nickname. If you need the bridge puppet to differ from a human's nick,
    set env ``BRIDGE_XMPP_PUPPET_NICK_SUFFIX`` (default: empty — no suffix).
    """
    suf = os.environ.get("BRIDGE_XMPP_PUPPET_NICK_SUFFIX", "")
    if not suf:
        return sanitized_nick
    if len(sanitized_nick) + len(suf) <= max_len:
        return sanitized_nick + suf
    return sanitized_nick[: max_len - len(suf)] + suf
