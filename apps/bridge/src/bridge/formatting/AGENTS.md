# Formatting

> Scope: `src/bridge/formatting/` — inherits [Bridge AGENTS.md](../../../AGENTS.md).

Stateless format converters between Discord, IRC, and XMPP, plus IRC message splitting and paste service integration.

## Files

| File | Purpose |
|------|---------|
| `discord_to_irc.py` | Strip Discord markdown to plain text for IRC; preserves URLs |
| `discord_to_xmpp.py` | Convert Discord markdown to XMPP XEP-0393 formatting |
| `irc_to_discord.py` | Convert IRC control codes to Discord markdown; strips colors; strikethrough `\x1e` → `~~` |
| `irc_to_xmpp.py` | Convert IRC control codes to XMPP XEP-0393 formatting |
| `xmpp_to_discord.py` | Convert XMPP XEP-0393 to Discord markdown |
| `xmpp_to_irc.py` | Convert XMPP XEP-0393 to IRC control codes |
| `irc_message_split.py` | Split long messages at IRC's byte limit, preserving word boundaries and UTF-8 |
| `paste.py` | Paste service integration for long messages |
| `reply_fallback.py` | Reply threading fallback when msgid unavailable |
| `mention_resolution.py` | Resolve `@nick` in IRC/XMPP content to Discord `<@userId>` via guild member lookup |

## `discord_to_irc.py`

`discord_to_irc(content)` — strips Discord markdown to plain text. Splits on URLs first so URL content is never modified.

`_strip_markdown(text)` handles: spoilers `||…||`, bold `**…**` / `__…__`, italic `*…*` / `_…_`, strikethrough `~~…~~`, code blocks ` ``` `, double backtick ` `` `, inline code `` ` ``.

## `irc_to_discord.py`

`irc_to_discord(content)` — converts IRC formatting to Discord markdown. Splits on URLs first.

Strips IRC color codes (`\x03NN`, `\x03N,N`, `\x04RRGGBB`). Converts:

- `\x02` (bold) → `**…**`
- `\x1d` (italic) → `*…*`
- `\x1f` (underline) → `__…__`
- `\x0f` (reset) — closes all open formatting

Escapes Discord markdown special chars (`* _ \` ~ |`) outside URLs. Closes any unclosed formatting at end of string.

## `irc_message_split.py`

`split_irc_message(content, max_bytes=450)` — splits UTF-8 content into chunks each ≤ `max_bytes` bytes.

- Default 450 bytes leaves room for `PRIVMSG #channel :` prefix and IRCv3 tag overhead
- Prefers word boundaries (splits at last space in first half of chunk)
- Never splits mid-UTF-8 multi-byte character
- Returns `[]` for empty input, `[content]` if already within limit

## Rules

- All functions are pure — no side effects, no I/O, no state.
- `discord_to_irc` and `irc_to_discord` are called by `relay.py` — do not call them from adapters directly.
- `split_irc_message` is called by the IRC adapter before sending, not by the relay.

## Related

- [gateway/AGENTS.md](../gateway/AGENTS.md)
- [bridge/AGENTS.md](../AGENTS.md)
- [Bridge AGENTS.md](../../../AGENTS.md)
