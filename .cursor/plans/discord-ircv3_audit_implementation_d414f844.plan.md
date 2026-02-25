---
name: discord-ircv3 audit implementation
overview: "Implement ideas from the discord-ircv3 reference audit: image embedding improvement, IRC strikethrough support, and mention resolution for cross-protocol pings."
todos:
  - id: image-embed
    content: "Discord adapter: fetch media URLs and send as File attachment"
    status: completed
  - id: irc-strikethrough
    content: "irc_to_discord: add \\x1e strikethrough to Discord ~~"
    status: completed
  - id: mention-resolution
    content: Resolve @nick in IRC/XMPP content to Discord user mention via guild member lookup
    status: completed
  - id: tests
    content: Add tests for strikethrough, media fetch, mention resolution
    status: completed
isProject: false
---

# discord-ircv3 Audit Implementation Plan

## Scope

Implements the high- and medium-priority ideas from the [discord-ircv3 audit](~/dev/allthingslinux/misc/bridge/references/discord-ircv3):

1. **Image embedding** — Fetch media URLs and send as `discord.File` attachment for reliable display
2. **IRC strikethrough** — Map IRC `\x1e` to Discord `~~`
3. **Mention resolution** — Resolve `@nick` in IRC/XMPP content to Discord `<@userId>` so pings work across protocols

---

## Phase 1: Image Embedding for Discord

**Current state:** When IRC users send image URLs, we relay the URL as message content. Discord may or may not embed it. `discord.File` requires bytes — no URL support. **Approach:** Fetch the URL, pass bytes to `discord.File`, send via webhook. Guaranteed display.

### 1.1 Detect image URLs

Add a pattern for common image/video URLs (jpg, jpeg, png, gif, webm, mp4) — same as discord-ircv3: `^https?://[^\s\x01-\x16]+\.(?:jpg|jpeg|png|gif|mp4|webm)$`

### 1.2 Fetch and send as File (stream to temp file)

When `evt.content` matches the media-only pattern:

1. Fetch the URL (aiohttp or httpx; timeout e.g. 10s)
2. **Stream to temp file** — write chunks to `tempfile.NamedTemporaryFile(delete=False)` as we read; stop if size exceeds limit (e.g. 10 MB). Avoids loading entire file into memory; `discord.File` accepts path via `fp=path`.
3. Extract filename from URL path or use fallback (e.g. `image.png`)
4. Create `discord.File(fp=temp_path, filename=...)`, send via webhook, then `os.unlink(temp_path)` (or use try/finally)
5. On fetch failure (timeout, 4xx/5xx, too large): fall back to sending URL as content (current behavior)

**Why stream to temp file:** Memory-efficient for large images; `discord.File(fp=path)` reads from disk on send. Compatible with async streaming (aiohttp `response.content.iter_chunked()`).

### 1.3 Webhook send with file

Extend `webhook_send` to accept `file: discord.File | None`. When `file` is provided, pass it to `webhook.send(file=file, ...)`. Reuse existing username, avatar_url, reply_to_id handling.

### 1.4 Scope

- **IRC → Discord only** — when MessageOut content is a media URL
- **Discord → IRC** — unchanged (already sends URL as `📎 filename: url`)

---

## Phase 2: IRC Strikethrough

**Current state:** [bridge/formatting/irc_to_discord.py](apps/bridge/src/bridge/formatting/irc_to_discord.py) handles bold, italic, underline. IRC strikethrough is `\x1e` (STRIKETHROUGH per IRCv3).

### 2.1 Add strikethrough handling

In `_convert_irc_codes`:

- Add `STRIKETHROUGH = "\x1e"` constant
- Add `strikethrough` state variable
- On `\x1e`: toggle strikethrough; output `~~` when closing, `~~` when opening
- On RESET: close strikethrough if open
- At end: close any unclosed strikethrough

---

## Phase 3: Mention Resolution (IRC/XMPP → Discord)

**Goal:** When someone on IRC or XMPP types `@kaizen` (or similar), resolve it to a Discord user mention `<@userId>` so the target gets pinged.

### 3.1 Pattern

Match `@identifier` in content where identifier is a username/nick to look up. Pattern: `@([^\s@#]+)` — capture after @ until whitespace, @, or #. Exclude `@everyone` and `@here` explicitly (do not resolve those).

### 3.2 Lookup via discord.utils

Use `discord.utils.find` or `discord.utils.get` — no Context needed, works directly on `guild.members`:

```python
# Case-insensitive match: nick, display_name, or name
def _match_member(m, identifier: str) -> bool:
    ident = identifier.lower()
    return (
        (m.nick and m.nick.lower() == ident)
        or (m.display_name and m.display_name.lower() == ident)
        or (m.name and m.name.lower() == ident)
    )
member = discord.utils.find(lambda m: _match_member(m, identifier), guild.members)
```

**Alternative:** `discord.utils.get(guild.members, name=identifier)` for exact username match; use `find` with a predicate when matching nick/display_name too.

**Cache-only:** `guild.members` is cached. For large guilds with uncached members, consider `MemberConverter` + fake Context as fallback (it can lazy-fetch via `query_members`). For typical bridge deployments, cache is sufficient.

### 3.3 Where to implement

- **Before webhook send** — when preparing MessageOut content for Discord target, run mention resolution
- **Requires bot + guild** — need `bot.get_channel(channel_id)` → `channel.guild` → member lookup. Webhook path already has bot for reply button; pass guild or bot to resolver
- **Skip inside code blocks** — do not resolve `@nick` inside backticks (preserve literal)

### 3.4 AllowedMentions

Current: `AllowedMentions(everyone=False, roles=False)`. User mentions are allowed by default. Resolved `<@userId>` will ping. No change needed unless we want to restrict to only explicitly resolved users.

### 3.5 Scope

- **IRC → Discord** — resolve `@nick` when IRC user types it
- **XMPP → Discord** — resolve `@nick` or JID localpart when XMPP user types it
- **Discord → IRC/XMPP** — unchanged (Discord mentions already show as display names or we strip)

---

## File Change Summary


| File                                                                                               | Changes                                                       |
| -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| [bridge/adapters/discord/adapter.py](apps/bridge/src/bridge/adapters/discord/adapter.py)           | Fetch media URLs; call mention resolution before webhook send |
| [bridge/adapters/discord/webhook.py](apps/bridge/src/bridge/adapters/discord/webhook.py)           | Extend webhook_send to accept file param                      |
| [bridge/formatting/mention_resolution.py](apps/bridge/src/bridge/formatting/mention_resolution.py) | New: resolve @nick to Discord user ID via guild member lookup |
| [bridge/formatting/irc_to_discord.py](apps/bridge/src/bridge/formatting/irc_to_discord.py)         | Add strikethrough `\x1e` handling                             |


---

## Out of Scope (Deferred)

- **Presence relay** — Join/Part/Kick/Quit as italicized messages (configurable via `announce_joins_and_quits`)
- **BOT mode** — Parse IRC 005 BOT= and set MODE (low value; add if needed)
- **NICK change relay** — "*old* is now known as *new*" (requires broadcast to all channels)
- **Discord→IRC preserve formatting** — Convert Discord markdown to IRC codes (high effort; would need parser)
- **Custom emoji resolution** — :emoji: → server emoji (requires guild emoji lookup)

---

## Testing

- Add formatting test for strikethrough in `test_formatting.py`
- Add test for media fetch/File send in Discord adapter tests
- Add test for mention resolution (mock guild/members, assert @nick → `<@id>`)

