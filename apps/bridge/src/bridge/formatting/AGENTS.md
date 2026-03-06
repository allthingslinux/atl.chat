# Formatting

> Scope: `src/bridge/formatting/` -- inherits [Bridge AGENTS.md](../../../AGENTS.md).

IR-based format conversion between Discord, IRC, and XMPP, plus message splitting and paste service integration.

## Architecture

All cross-protocol formatting goes through an intermediate representation (IR):

```
Source format -> parse -> FormattedText IR -> emit -> Target format
```

The `converter.py` registry dispatches to protocol-specific parsers and emitters.

## Files

| File | Purpose |
|------|---------|
| `primitives.py` | `FormattedText`, `Span`, `Style` (flag enum), `CodeBlock` IR types; `URL_RE`, `FENCE_RE`, `ZWS_RE` shared regex; `irc_casefold`, `strip_invalid_xml_chars` |
| `converter.py` | `convert(content, origin, target)` registry; `strip_formatting(content, protocol)` |
| `markdown.py` | Discord markdown parser (`parse_discord_markdown`) and emitter (`emit_discord_markdown`) |
| `irc_codes.py` | IRC control code parser (`parse_irc_codes`) and emitter (`emit_irc_codes`); `detect_irc_spoilers` |
| `xmpp_styling.py` | XEP-0393 parser (`parse_xep0393`) and emitter (`emit_xep0393`); XEP-0394 emitter (`emit_xep0394`) |
| `splitter.py` | `split_irc_message(content, max_bytes)` -- byte-safe UTF-8 splitting; `split_irc_lines` -- newline-aware wrapper; `extract_code_blocks` -- fenced code block extraction for paste upload |
| `paste.py` | PrivateBin paste service integration for long messages |
| `mention_resolution.py` | Resolve `@nick` in IRC/XMPP content to Discord `<@userId>` via guild member lookup |
| `reply_fallback.py` | Reply threading fallback when msgid unavailable |
| `discord_to_xmpp.py` | Discord markdown to XEP-0393 body + XEP-0394 spans (used by XMPP adapter for rich markup) |

## IR Types (`primitives.py`)

- `Style` -- flag enum: `BOLD`, `ITALIC`, `UNDERLINE`, `STRIKETHROUGH`, `MONOSPACE`, `SPOILER`
- `Span(start, end, style)` -- styled region within plain text
- `CodeBlock(language, content, start, end)` -- fenced code block
- `FormattedText(plain, spans, code_blocks)` -- complete IR

## Rules

- All IR functions are pure -- no side effects, no I/O, no state.
- `convert()` is called by pipeline steps in `gateway/steps.py` -- do not call from adapters directly.
- `split_irc_message` is called by the IRC adapter before sending, not by the relay.
- URLs are protected from formatting parsing (XEP-0393 parser skips URL regions).

## Related

- [gateway/AGENTS.md](../gateway/AGENTS.md)
- [bridge/AGENTS.md](../AGENTS.md)
- [Bridge AGENTS.md](../../../AGENTS.md)
