# Identity

> Scope: `src/bridge/identity/` -- inherits [Bridge AGENTS.md](../../../AGENTS.md).

Portal API integration and identity resolution across protocols. Maps Discord users to IRC nicks and XMPP JIDs (and vice versa) via the Portal service, with a TTL cache.

## Files

| File | Purpose |
|------|---------|
| `base.py` | `IdentityResolver` ABC; `DevIdentityResolver` (returns `None` for all lookups -- used when Portal is unavailable) |
| `portal.py` | `PortalClient` (httpx + tenacity retries), `PortalIdentityResolver` (wraps client with TTLCache) |
| `dev.py` | `DevIdentityResolver` legacy alias (imports from `base.py`) |
| `sanitize.py` | `ensure_valid_username(name)` -- cleans webhook display names; `sanitize_nick(nick)` -- strips invalid IRC nick characters |

## PortalClient (`portal.py`)

- Uses httpx async client with Bearer token auth
- Retries on transient HTTP errors (5 attempts, exponential backoff 2–30s via tenacity)
- Returns `None` on 404 -- never raises for missing identity

## IdentityResolver (`base.py`)

ABC with lookup methods:

- `discord_to_irc(discord_id)` → IRC nick or `None`
- `discord_to_xmpp(discord_id)` → XMPP JID or `None`
- `irc_to_discord(nick, server?)` → Discord ID or `None`
- `xmpp_to_discord(jid)` → Discord ID or `None`
- `has_irc(discord_id)` / `has_xmpp(discord_id)` → bool

## Related

- [bridge/AGENTS.md](../AGENTS.md)
- [Bridge AGENTS.md](../../../AGENTS.md)
