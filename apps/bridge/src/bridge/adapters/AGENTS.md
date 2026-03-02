# Adapters

> Scope: `src/bridge/adapters/` — inherits [Bridge AGENTS.md](../../../AGENTS.md).

Protocol-specific adapters. Each registers with the Bus, filters events via `accept_event`, and handles them via `push_event`.

## Layout (AUDIT §2.B)

```
adapters/
├── __init__.py
├── base.py
├── discord/
│   ├── __init__.py
│   ├── adapter.py      # DiscordAdapter (orchestrator)
│   ├── handlers.py     # handle_delete_out, handle_reaction_out, handle_typing_out, handle_attachments
│   └── webhook.py      # get_or_create_webhook, webhook_send, webhook_edit, _reply_button_view
├── irc/
│   ├── __init__.py
│   ├── adapter.py      # IRCAdapter
│   ├── client.py       # IRCClient (pydle)
│   ├── msgid.py        # MessageIDTracker, ReactionTracker, MessageMapping
│   ├── puppet.py       # IRCPuppet, IRCPuppetManager
│   └── throttle.py     # TokenBucket
└── xmpp/
    ├── __init__.py
    ├── adapter.py      # XMPPAdapter
    ├── component.py    # XMPPComponent
    └── msgid.py        # XMPPMessageIDTracker, XMPPMessageMapping
```

## Critical Rules

- Adapters must never import each other — all cross-adapter communication goes through the Bus only.
- Discord adapter uses `on_raw_*` events exclusively — never the cached variants.
- `AllowedMentions(everyone=False, roles=False)` on every webhook send.
- IRC puppet pinger task must be cancelled in `on_disconnect` / cleanup to avoid task leaks.
- XMPP and IRC msgid trackers are the source of truth for edit/delete routing to Discord.

## Discord Adapter (`discord/`)

Env: `BRIDGE_DISCORD_TOKEN`.

- **adapter.py** — `DiscordAdapter`: orchestrator, queue consumer, event wiring.
- **handlers.py** — Outbound handlers: `handle_delete_out`, `handle_reaction_out`, `handle_typing_out`, `handle_attachments`.
- **webhook.py** — `get_or_create_webhook`, `webhook_send`, `webhook_edit`, `_reply_button_view`, `_ensure_valid_username`.

Outbound events (`MessageOut`, `MessageDeleteOut`, `ReactionOut`, `TypingOut`) are queued (`asyncio.Queue`) and consumed with a 250ms delay to avoid rate limits. One webhook per channel (matterbridge pattern); username/avatar per message in `webhook.send()`. Edit flow: `MessageOut.raw["is_edit"]` → resolve Discord message ID via IRC/XMPP msgid tracker → `webhook.edit_message`. Delete flow: `MessageDeleteOut` → `handle_delete_out` → `channel.fetch_message` + `msg.delete()`. Reaction removes carry `raw={"is_remove": True}` through the relay. Bulk delete (`on_raw_bulk_message_delete`) iterates and emits one `MessageDeleteOut` per message. `!bridge status` slash command reports adapter health.

## IRC Adapter (`irc/`)

Env: `BRIDGE_IRC_NICK` (default: `bridge`).

**client.py** — `IRCClient` (pydle.Client):

- IRCv3 capability negotiation on connect; `_ready_fallback` joins channels if `RPL_005` not received.
- `on_message` / `on_ctcp_action` — emit `MessageIn` to Bus.
- `on_raw_tagmsg` — handles `+draft/reply` (threading), `+draft/react` (add), `+draft/unreact` (remove).
- `on_raw_redact` — handles IRCv3 REDACT; emits `MessageDelete`.
- `on_kick` — emits `Part`; auto-rejoins after `irc_rejoin_delay` if `irc_auto_rejoin` is set.
- `on_disconnect` — reconnects with exponential backoff via `_connect_with_backoff`.
- Outbound queue consumed by `_consume_outbound`; uses `TokenBucket` for flood control.
- **RELAYMSG**: When server advertises `draft/relaymsg` or `overdrivenetworks.com/relaymsg`, main-connection sends use `RELAYMSG #channel nick/d :message`. Echo detection: skip messages with matching relaymsg tag.
- Typing: `TAGMSG` with `typing=active`, throttled to once per 3 seconds.
- Reactions: add via `TAGMSG` with `+draft/reply` + `+draft/react`; remove via `+draft/unreact`.
- Deletes: `REDACT` command with original IRC msgid.

**adapter.py** — `IRCAdapter`:

- Accepts `MessageOut`, `MessageDeleteOut`, `ReactionOut`, `TypingOut` targeting `"irc"`.
- Routes `MessageOut` via puppet if identity available, otherwise falls back to main connection.
- Starts `IRCPuppetManager` if `IdentityResolver` is present.
- SASL PLAIN auth if `irc_use_sasl` + `irc_sasl_user` + `irc_sasl_password` are set.

**puppet.py** — `IRCPuppet`, `IRCPuppetManager`:

- `IRCPuppet` extends `pydle.Client`; tracks `last_activity` for idle timeout.
- **METADATA avatar sync**: When `avatar_url` is provided and server supports `draft/metadata`, puppets set `METADATA * SET avatar :url` before sending.
- On connect: sends `irc_puppet_prejoin_commands`, starts `_pinger` task.
- `IRCPuppetManager.get_or_create_puppet(discord_id)` — resolves IRC nick via `IdentityResolver`, connects if new.
- Idle cleanup runs every hour; disconnects puppets inactive for `irc_puppet_idle_timeout_hours`.

**msgid.py** — `MessageIDTracker`, `ReactionTracker`, `MessageMapping`:

- Bidirectional `irc_msgid ↔ discord_id` map with manual TTL cleanup (1h default).
- `store(irc_msgid, discord_id)`, `get_discord_id(irc_msgid)`, `get_irc_msgid(discord_id)`.

**throttle.py** — `TokenBucket(limit, refill_rate=1.0)`:

- `use_token()` → `True` if token available, `False` if bucket empty.
- `acquire()` → seconds to wait before a token is available.

## XMPP Adapter (`xmpp/`)

Env: `BRIDGE_XMPP_COMPONENT_JID`, `BRIDGE_XMPP_COMPONENT_SECRET`, `BRIDGE_XMPP_COMPONENT_SERVER`, `BRIDGE_XMPP_COMPONENT_PORT` (default: 5347).

**adapter.py** — `XMPPAdapter`:

- Disabled at startup if any of JID/secret/server are missing, or no XMPP mappings.
- Outbound queue (250ms delay) drains `MessageOut`, `MessageDeleteOut`, `ReactionOut`.
- Edit flow: looks up original XMPP message ID via msgid tracker → `send_correction_as_user`.
- Delete flow: looks up XMPP ID → `send_retraction_as_user`.
- Reaction flow: looks up XMPP ID → `send_reaction_as_user`.
- Nick resolution: `identity.discord_to_xmpp(author_id)` when Portal present; otherwise fallback nicks.

**component.py** — `XMPPComponent` (slixmpp `ComponentXMPP`):

- XEPs: 0030, 0045, 0047 (IBB), 0054 (vCard), 0106 (JID Escaping), 0198, 0199, 0203, 0308, 0363, 0372, 0382, 0422, 0424, 0444, 0461.
- `send_message_as_user`, `send_correction_as_user`, `send_retraction_as_user`, `send_reaction_as_user`, `send_file_with_fallback`, `set_avatar_for_user`, `join_muc_as_user`.
- Inbound: `_on_groupchat_message`, `_on_reactions`, `_on_retraction`.

**msgid.py** — `XMPPMessageIDTracker`, `XMPPMessageMapping`:

- Bidirectional `xmpp_id ↔ discord_id` map with `room_jid`, TTL cleanup.
- `store`, `add_alias`, `add_stanza_id_alias`, `get_discord_id`, `get_xmpp_id`, `get_xmpp_id_for_reaction`, `get_room_jid`.

## Related

- [Bridge AGENTS.md](../../../AGENTS.md)
- [gateway/AGENTS.md](../gateway/AGENTS.md)
- [bridge/AGENTS.md](../AGENTS.md)
- [tests/AGENTS.md](../../../tests/AGENTS.md)
