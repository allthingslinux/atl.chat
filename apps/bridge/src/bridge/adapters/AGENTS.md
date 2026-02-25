# Adapters

> Scope: `src/bridge/adapters/` — inherits [Bridge AGENTS.md](../../../AGENTS.md).

Protocol-specific adapters. Each registers with the Bus, filters events via `accept_event`, and handles them via `push_event`.

## Files

| File | Purpose |
|------|---------|
| `base.py` | `AdapterBase` ABC — `name`, `accept_event`, `push_event`, `start`, `stop` |
| `disc.py` | Discord adapter: webhooks, raw event handlers, outbound queue |
| `irc.py` | IRC adapter: `IRCClient` (pydle) + `IRCAdapter`; IRCv3 caps, puppet routing |
| `irc_puppet.py` | `IRCPuppet` (pydle.Client) + `IRCPuppetManager`: per-user connections, idle timeout, keep-alive |
| `irc_throttle.py` | `TokenBucket`: token bucket flood control for IRC sends |
| `irc_msgid.py` | `MessageIDTracker`, `ReactionTracker`, `ReactionMapping`: IRC msgid ↔ Discord ID map; reaction removal (REDACT) |
| `xmpp.py` | `XMPPAdapter`: outbound queue, routes to `XMPPComponent` |
| `xmpp_component.py` | `XMPPComponent` (slixmpp `ComponentXMPP`): XEPs, MUC presence, file upload, avatar sync |
| `xmpp_msgid.py` | `XMPPMessageIDTracker`: XMPP stanza-id ↔ Discord ID map; `add_alias`, `add_stanza_id_alias` for edit/reaction lookup |

## Critical Rules

- Adapters must never import each other — all cross-adapter communication goes through the Bus only.
- Discord adapter uses `on_raw_*` events exclusively — never the cached variants.
- `AllowedMentions(everyone=False, roles=False)` on every webhook send.
- IRC puppet pinger task must be cancelled in `on_disconnect` / cleanup to avoid task leaks.
- XMPP and IRC msgid trackers are the source of truth for edit/delete routing to Discord.

## Discord Adapter (`disc.py`)

Env: `BRIDGE_DISCORD_TOKEN`.

- Outbound events (`MessageOut`, `MessageDeleteOut`, `ReactionOut`, `TypingOut`) are queued (`asyncio.Queue`) and consumed with a 250ms delay to avoid rate limits.
- One webhook per channel (matterbridge pattern); username/avatar per message in `webhook.send()`.
- Edit flow: `MessageOut.raw["is_edit"]` → resolve Discord message ID via IRC/XMPP msgid tracker → `webhook.edit_message`.
- Delete flow: `MessageDeleteOut` → resolve Discord message ID → `webhook.delete_message`.
- Reaction removes carry `raw={"is_remove": True}` through the relay to target adapters.
- Bulk delete (`on_raw_bulk_message_delete`) iterates and emits one `MessageDeleteOut` per message.
- Attachment handling: downloads and re-uploads files to bridged channels.
- `_ensure_valid_username(name)` sanitizes webhook usernames for Discord's requirements.
- `!bridge status` slash command reports adapter health.

## IRC Adapter (`irc.py`)

Env: `BRIDGE_IRC_NICK` (default: `atl-bridge`).

Two classes:

**`IRCClient`** (pydle.Client) — main IRC connection:

- IRCv3 capability negotiation on connect; `_ready_fallback` joins channels if `RPL_005` not received.
- `on_message` / `on_ctcp_action` — emit `MessageIn` to Bus.
- `on_raw_tagmsg` — handles `+draft/reply` (threading), `+draft/react` (add), `+draft/unreact` (remove).
- `on_raw_redact` — handles IRCv3 REDACT; emits `MessageDelete`.
- `on_kick` — emits `Part`; auto-rejoins after `irc_rejoin_delay` if `irc_auto_rejoin` is set.
- `on_disconnect` — reconnects with exponential backoff via `_connect_with_backoff`.
- Outbound queue consumed by `_consume_outbound`; uses `TokenBucket` for flood control.
- **RELAYMSG**: When server advertises `draft/relaymsg` or `overdrivenetworks.com/relaymsg`, main-connection sends use `RELAYMSG #channel nick/d :message` (stateless bridging) instead of `PRIVMSG`. Spoofed nick format: `author_display/discord` (Valware requires `/` in nick). Echo detection: skip messages with `draft/relaymsg` or `relaymsg` tag matching our nick.
- Typing: `TAGMSG` with `typing=active`, throttled to once per 3 seconds.
- Reactions: add via `TAGMSG` with `+draft/reply` + `+draft/react`; remove via `TAGMSG` with `+draft/reply` + `+draft/unreact` (IRCv3 spec).
- Deletes: `REDACT` command with original IRC msgid.

**`IRCAdapter`** — Bus-facing wrapper:

- Accepts `MessageOut`, `MessageDeleteOut`, `ReactionOut`, `TypingOut` targeting `"irc"`.
- Routes `MessageOut` via puppet if identity available, otherwise falls back to main connection.
- Starts `IRCPuppetManager` if `IdentityResolver` is present.
- SASL PLAIN auth if `irc_use_sasl` + `irc_sasl_user` + `irc_sasl_password` are set.

## IRC Puppet Manager (`irc_puppet.py`)

- `IRCPuppet` extends `pydle.Client`; tracks `last_activity` for idle timeout.
- **METADATA avatar sync**: When `avatar_url` is provided and server supports `draft/metadata`, puppets set `METADATA * SET avatar :url` before sending. Cached by hash to avoid redundant updates.
- On connect: sends `irc_puppet_prejoin_commands` (supports `{nick}` substitution), starts `_pinger` task.
- `_pinger` sends `PING keep-alive` every `irc_puppet_ping_interval` seconds.
- `IRCPuppetManager.get_or_create_puppet(discord_id)` — resolves IRC nick via `IdentityResolver`, connects if new.
- Idle cleanup runs every hour; disconnects puppets inactive for `irc_puppet_idle_timeout_hours`.
- `send_message` splits content via `split_irc_message(max_bytes=450)` before sending.

## IRC Message ID Tracker (`irc_msgid.py`)

**`MessageIDTracker`** — bidirectional `irc_msgid ↔ discord_id` map with manual TTL cleanup (1h default).

- `store(irc_msgid, discord_id)` — stores both directions.
- `get_discord_id(irc_msgid)` → Discord ID or `None`.
- `get_irc_msgid(discord_id)` → IRC msgid or `None`.
- `_cleanup()` called on every read; removes entries older than TTL.

**`ReactionTracker`** + **`ReactionMapping`** — Inbound IRC reaction REDACT fallback: when a client REDACTs a reaction TAGMSG, maps irc_msgid → Discord message ID. Outbound removal uses `+draft/unreact` (no tracker needed).

## IRC Throttle (`irc_throttle.py`)

`TokenBucket(limit, refill_rate=1.0)`:

- `use_token()` → `True` if token available (consumes it), `False` if bucket empty.
- `acquire()` → seconds to wait before a token is available (0 if available now).
- Refills continuously based on elapsed time since last refill.

## XMPP Adapter (`xmpp.py`)

Env: `BRIDGE_XMPP_COMPONENT_JID`, `BRIDGE_XMPP_COMPONENT_SECRET`, `BRIDGE_XMPP_COMPONENT_SERVER`, `BRIDGE_XMPP_COMPONENT_PORT` (default: 5347).

- Disabled at startup if any of JID/secret/server are missing, or no XMPP mappings. Runs without Portal (identity resolver) for dev: uses fallback nicks (author_id, then author_display).
- Outbound queue (250ms delay) drains `MessageOut`, `MessageDeleteOut`, `ReactionOut`.
- Edit flow: looks up original XMPP message ID via `_msgid_tracker.get_xmpp_id(discord_id)` → `send_correction_as_user`.
- Delete flow: looks up XMPP ID → `send_retraction_as_user`.
- Reaction flow: looks up XMPP ID → `send_reaction_as_user`.
- Nick resolution: `identity.discord_to_xmpp(author_id)` when Portal present; otherwise `author_id` or `author_display` (dev mode).
- Avatar sync: calls `set_avatar_for_user` before sending if `evt.avatar_url` is set.

## XMPP Component (`xmpp_component.py`)

`XMPPComponent` extends slixmpp `ComponentXMPP`. Registered XEPs:

| XEP | Purpose |
|-----|---------|
| 0030 | Service Discovery |
| 0045 | Multi-User Chat |
| 0047 | In-Band Bytestreams (IBB) — file transfer fallback |
| 0054 | vCard-temp — avatar sync |
| 0106 | JID Escaping |
| 0198 | Stream Management (resume enabled) |
| 0199 | XMPP Ping (keepalive: 180s interval, 30s timeout) |
| 0203 | Delayed Delivery — filtered to prevent history replay on join |
| 0308 | Last Message Correction — edits |
| 0363 | HTTP File Upload — primary file transfer |
| 0372 | References |
| 0382 | Spoiler Messages |
| 0422 | Message Fastening |
| 0424 | Message Retraction — deletes |
| 0444 | Message Reactions |
| 0461 | Message Replies — threading |

Key methods:

- `send_message_as_user(discord_id, muc_jid, content, nick, reply_to_id?)` — sends MUC message as puppet JID; returns XMPP message ID.
- `send_correction_as_user(...)` — XEP-0308 correction.
- `send_retraction_as_user(...)` — XEP-0424 retraction.
- `send_reaction_as_user(...)` — XEP-0444 reaction.
- `send_file_with_fallback(...)` — HTTP Upload (XEP-0363) with IBB (XEP-0047) fallback.
- `set_avatar_for_user(discord_id, nick, avatar_url)` — vCard-temp avatar sync; cached by `avatar_hash`.
- `join_muc_as_user(muc_jid, nick)` — joins MUC as puppet.

Inbound handlers:

- `_on_groupchat_message` — emits `MessageIn` to Bus; skips delayed delivery (XEP-0203). Builds `avatar_url` via `_resolve_avatar_url`: tries `/pep_avatar/{node}` first, then `/avatar/{node}` (vCard) as fallback. Cached by (domain, node).
- `_on_reactions` — emits `ReactionIn` to Bus.
- `_on_retraction` — emits `MessageDelete` to Bus.

## XMPP Message ID Tracker (`xmpp_msgid.py`)

`XMPPMessageIDTracker` — bidirectional `xmpp_id ↔ discord_id` map with `room_jid`, manual TTL cleanup (1h default).

- `store(xmpp_id, discord_id, room_jid)` — stores both directions.
- `add_alias(alias_id, primary_xmpp_id)` — add alias for `get_discord_id` (e.g. origin-id when primary is stanza-id).
- `add_stanza_id_alias(our_id, stanza_id)` — add stanza-id alias (reactions use stanza-id; corrections use our_id).
- `get_discord_id(xmpp_id)` → Discord ID or `None`.
- `get_xmpp_id(discord_id)` → XMPP message ID or `None`.
- `get_xmpp_id_for_reaction(discord_id)` → prefers stanza-id when available.
- `get_room_jid(discord_id)` → room JID or `None`.

## Related

- [Bridge AGENTS.md](../../../AGENTS.md)
- [gateway/AGENTS.md](../gateway/AGENTS.md)
- [bridge/AGENTS.md](../AGENTS.md)
- [tests/AGENTS.md](../../../tests/AGENTS.md)
