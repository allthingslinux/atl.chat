# Bridge Codebase Audit

Master checklist of every source file with known bugs, race conditions, and edge cases.
Each item is a discrete fix. Check off when resolved.

> Second-pass audit completed — every file read in full.

---

## Legend

- 🔴 HIGH — crash, data corruption, security issue, resource leak in normal operation
- 🟡 MEDIUM — logic bug, race condition under load, incorrect edge-case behaviour
- 🟢 LOW — minor inefficiency, unclear code, potential future issue
- ✅ — verified clean (read in full, no issues found)

---

## `src/bridge/__main__.py`

- [ ] 🟡 **Adapter stop timeout** — `adapter.stop()` calls have no timeout; a hanging adapter blocks the entire shutdown loop forever (line ~304)
- [ ] 🟢 **Redundant `import os`** — `os` is imported at module level and again inside `_get_portal_url`, `_dev_irc_puppets_enabled`, `_get_portal_token`; remove inner imports

---

## `src/bridge/avatar.py`

- [ ] 🟡 **Cache rebuild race** — `_get_cache()` replaces the global `_avatar_url_cache` without a lock; two concurrent callers during config reload can operate on different cache objects, producing inconsistent lookups (lines ~14–19)
- [ ] 🟡 **HEAD probe connect timeout** — `timeout=1.5` applies to the read but httpx's default connect timeout is 5 s; pass `httpx.Timeout(total=3.0)` to the `AsyncClient` constructor so a non-responding Prosody never blocks longer than expected
- [ ] 🟢 **Overly broad `except Exception`** — the outer catch swallows `MemoryError`, `SystemExit`, and other non-recoverable errors; catch `(httpx.HTTPError, OSError)` instead (lines ~116–118)

---

## `src/bridge/adapters/discord/adapter.py`

- [ ] 🔴 **Echo-label queue-empty crash** — `pending_sends.get_nowait()` (line ~172) raises `asyncio.QueueEmpty` with no try/except when an echo arrives but the send queue is empty; message-ID correlation is silently lost and the exception propagates uncaught
- [ ] 🔴 **Webhook send / ID mapping race** — the Discord→XMPP/IRC message-ID mapping is stored *after* the webhook send returns (lines ~381–421); a concurrent REDACT arriving between the send and the store finds nothing and silently fails
- [ ] 🟡 **Stale webhook not evicted on 404** — if a webhook is deleted by a Discord moderator, the cached `Webhook` object is reused for up to 24 h; 404 responses from Discord should immediately evict the entry from `_webhook_cache` (lines ~225–239)
- [ ] 🟡 **Message dropped on webhook failure** — an unhandled exception in the queue consumer logs the error but does not re-queue the event; the message is silently lost (line ~426)

---

## `src/bridge/adapters/discord/avatar.py`

- [ ] 🟢 **localhost avatar URL returned to Discord** — `resolve_xmpp_avatar_fallback` can return URLs containing `localhost` / `127.0.0.1` that Discord's CDN cannot reach; filter these out before returning (line ~36)

---

## `src/bridge/adapters/discord/handlers.py`

- [ ] 🟡 **Silent fetch failure on edit** — when `payload.message` is None, `fetch_message` failure is caught silently with no log; should warn so operators can detect message-intent loss (lines ~238–246)
- [ ] 🟢 **Negative attachment dimension** — `attachment.width` / `attachment.height` can theoretically be negative in a malformed Discord payload; downstream XEP-0446 metadata would contain invalid values; add `> 0` guard (lines ~130–132)

---

## `src/bridge/adapters/discord/media.py`

- [ ] 🔴 **File descriptor leak on exception** — if an exception occurs between `os.open` / `mkstemp` and `os.close(fd)`, the file descriptor leaks; the close must be in a `try/finally` (lines ~116–139)
- [ ] 🟡 **Double unlink on error path** — on non-200 HTTP status the file is unlinked; the outer `except` block also calls `os.unlink` on the same path, raising a spurious `FileNotFoundError` that masks the original error (lines ~124–139)
- [ ] 🟡 **Full download before size limit check** — the streaming loop writes each chunk then checks `total > MEDIA_SIZE_LIMIT`; a 100 MB file is fully written before being rejected; break out of the loop as soon as the limit is crossed (lines ~125–132)
- [ ] 🟡 **Temp file unlinked before webhook send** — `temp_path` is unlinked inside this function, but the webhook send (which reads the file) may be async and reference the path afterward; unlink only after the send completes (lines ~377–379)

---

## `src/bridge/adapters/discord/outbound.py`

- [ ] 🟡 **No timeout on identity lookup in attachment path** — `discord_to_xmpp` is awaited without a timeout; a slow Portal response blocks the entire attachment-bridging coroutine (lines ~115–119)
- [ ] 🟢 **Silent skip of oversized attachments** — files >10 MB are skipped with a bare `continue`; users get no indication their attachment was not bridged (line ~125)

---

## `src/bridge/adapters/discord/reply_emoji.py`

- [ ] 🟢 **Hardcoded asset path** — `_ASSETS_DIR` is resolved as `Path(__file__).parent.parent.parent / "assets"`; if the module is moved or installed as a package, the path silently breaks (line ~20)

---

## `src/bridge/adapters/discord/webhook.py`

- [ ] 🟡 **No lock around webhook cache check + create** — between reading the cache (line ~104) and creating a new webhook (line ~107), a concurrent request can trigger a duplicate creation; serialize per-channel with an `asyncio.Lock`
- [ ] 🟢 **Multi-instance webhook name collision** — two bridge instances reuse the first webhook named `"ATL Bridge"` they find; messages can appear to originate from the wrong instance's connection

---

## `src/bridge/adapters/irc/adapter.py`

- [ ] 🟡 **Untracked fire-and-forget tasks** — `asyncio.create_task` at lines ~72, ~76, ~80 uses `# noqa: RUF006` but tasks are not added to any tracking set; GC can cancel in-flight tasks and exceptions are silently swallowed (the puppet tasks at line ~85 are tracked correctly — only the earlier three are not)

---

## `src/bridge/adapters/irc/client.py`

- [ ] 🔴 **Label counter grows without bound** — `_label_counter` is an unbounded Python `int` that increments every message; in a long-running instance the label string grows to megabytes; cap with `% 1_000_000` (line ~389)
- [ ] 🟡 **Message tags shared across concurrent handlers** — `_message_tags` is stored on `self` and cleared in a `finally` block; two near-simultaneous `PRIVMSG` events mean handler 2 can read tags written by handler 1 before handler 1's `finally` fires; use a local variable instead (lines ~299–311)
- [ ] 🟡 **Nick collision counter never resets** — `_nick_collision_attempts` increments on every 433 but is never reset after a successful nick registration; a later collision starts from a stale high suffix (lines ~605–614)
- [ ] 🟡 **OPER sent without waiting for confirmation** — `rawmsg("OPER")` is sent and `asyncio.sleep(1)` is used as a proxy for the server accepting it; should wait for `RPL_YOUREOPER` (381) before sending MODE commands (lines ~204–216)
- [ ] 🟢 **Label TTL may be too short** — `_pending_labels` TTLCache uses 30 s; servers under load can echo messages after >30 s, causing silent label/ID correlation loss (line ~152)

---

## `src/bridge/adapters/irc/handlers.py`

- [ ] 🟡 **History replay threshold not configurable** — messages with server-time >30 s in the past are silently dropped; if the server clock is ahead of the bridge, legitimate recent messages are discarded; expose as a config value (lines ~136–142)
- [ ] 🟡 **ISO 8601 `Z` suffix rejected on Python <3.11** — `datetime.fromisoformat()` rejects `"2024-01-01T12:00:00Z"`; replace `Z` → `+00:00` before parsing (lines ~107–112)
- [ ] 🟡 **Duplicate label-pop race** — two concurrent echo handlers can both find the same label key before either pops it; make idempotent with `.pop(label, None)` and discard on `None` (lines ~161–190)
- [ ] 🟢 **Reactions silently dropped on missing msgid** — when an IRC msgid has no tracker entry, the reaction is silently dropped at DEBUG; users have no indication (lines ~303–306, ~335–338)

---

## `src/bridge/adapters/irc/msgid.py`

- [ ] 🟡 **Numeric IRC msgid misclassified as Discord snowflake** — `_is_discord_snowflake` uses `str.isdigit()`; IRC servers (znc, bouncers) can emit numeric msgids that are misclassified, corrupting REDACT skip logic (line ~43)
- [ ] 🟡 **Dangling reverse entries after cleanup** — `_cleanup()` removes expired forward keys but may leave reverse-map entries pointing at deleted forward entries if the same `discord_id` appears as a reversed key (lines ~98–108)

---

## `src/bridge/adapters/irc/outbound.py`

- [ ] 🟡 **Paste fallback exposes content in channel logs** — when paste upload fails, a truncated inline snippet is sent to IRC; content intended to be ephemeral (paste link) becomes permanently visible in channel history (lines ~91–96)

---

## `src/bridge/adapters/irc/puppet.py`

- [ ] 🟡 **`_puppet_locks` grows without bound** — one `asyncio.Lock` per `discord_id` is created and never evicted; with thousands of users the dict grows indefinitely; replace with `TTLCache` (line ~114)
- [ ] 🟡 **Nick revert failure leaves puppet with wrong nick** — if the `on_nick` revert attempt throws, the puppet keeps the server-assigned nick and all subsequent messages appear under the wrong name (lines ~54–62)

---

## `src/bridge/adapters/xmpp/adapter.py`

- [ ] 🟡 **Outbound message queue unbounded** — `asyncio.Queue()` has no `maxsize`; if Discord relays messages faster than XMPP can deliver them, the queue grows without limit and causes OOM (line ~84)
- [ ] 🟡 **Typing-done task race** — two `TypingOut` events for the same MUC arriving before the first done-task fires create two done-tasks; both send `<paused/>`, producing a spurious double-paused on XMPP clients (lines ~164+)

---

## `src/bridge/adapters/xmpp/avatar.py`

- [ ] 🟢 **Overly broad `except Exception` in avatar probe** — `MemoryError`, `KeyboardInterrupt` etc. are caught and silently return `None`; narrow to `(httpx.HTTPError, OSError)` (lines ~80–85)

---

## `src/bridge/adapters/xmpp/component.py`

- [ ] 🟡 **JID unescape passes through invalid hex sequences** — `_unescape_jid_node` replaces `\\XX` hex sequences, but sequences with non-hex digits (e.g., `\ZZ`) are passed through unchanged, potentially producing invalid JID node parts (lines ~49–56)
- [ ] 🟡 **MUC nick→JID result not validated** — `_muc_nick_to_bare_jid` can return a string that is not a valid JID; callers pass it directly to `JID()`, which raises an unhelpful `ValueError` with no surrounding context (lines ~59–80)

---

## `src/bridge/adapters/xmpp/handlers.py`

- [ ] 🟡 **Unsafe nick extraction from JID** — `full_jid.split("/")` assumes exactly one `/`; a resource containing `/` (invalid in MUC but possible from a buggy client) produces an incorrect nick for all downstream operations (line ~135)

---

## `src/bridge/adapters/xmpp/outbound.py`

- [ ] 🟡 **Reply body not explicitly XML-escaped** — `reply_to_body[:200]` is passed directly to `add_quoted_fallback()`; slixmpp should escape internally, but if it does not, raw `<`, `>`, `&` in quoted content will malform the stanza (line ~113)

---

## `src/bridge/adapters/xmpp/msgid.py`

- [ ] 🟡 **Cleanup on every operation is O(n)** — `_cleanup()` scans all mappings on every `store()` / `get()` call; under high message rate this is O(n) overhead per operation; throttle to at most once per second or move to a background task
- [ ] 🟢 **Alias update uses implicit reference equality** — `update_discord_id` finds aliases by `is`-equality; the aliasing relationship is implicit and fragile; track aliases explicitly

---

## `src/bridge/config/loader.py`

- [ ] 🟡 **Bool fields silently accept ints** — `0` / `1` pass bool validation; `irc_tls_verify: 0` disables TLS verification with no warning (lines ~82–84)
- [ ] 🟢 **Malformed config produces empty config silently** — YAML parse errors log a warning but return `{}`, allowing the bridge to start with zero mappings (lines ~124–132)

---

## `src/bridge/config/schema.py`

- [ ] 🟡 **YAML string `"false"` coerces to `True`** — boolean fields pass through Python's `bool()` which treats any non-empty string as truthy; `irc_auto_rejoin: "false"` becomes `True` instead of `False`; use explicit string-to-bool parsing (lines ~104–112)

---

## `src/bridge/formatting/splitter.py`

- [ ] 🟡 **UTF-8 boundary detection is heuristic** — the byte-boundary scan uses assumptions about multi-byte character structure; corrupted or non-standard UTF-8 input can produce invalid character boundaries and garbled output chunks (lines ~106–116)

---

## `src/bridge/gateway/relay.py`

- [ ] 🟡 **Content filter list replaced non-atomically** — `rebuild_content_filters()` writes to the module-level `_compiled_filters` list without a lock; a message filtered at the exact moment of a reload can read a partially-replaced list (lines ~48–92)
- [ ] 🟢 **Invalid regex silently disables filter** — a typo in `content_filter_regex` logs a warning and skips the bad pattern; if that pattern was meant to block spam, the bridge silently becomes less safe (line ~58)

---

## `src/bridge/gateway/msgid_resolver.py`

- [ ] 🟡 **Protocol name strings not validated** — a typo in a call site creates a new sub-map that is never matched, silently breaking message-ID correlation with no error (lines ~53–77)
- [ ] 🟡 **TTLCache eviction causes lost correlations under load** — when `_irc_xmpp_pending` reaches 2 000 entries, the oldest entries are evicted; REDACT / edit operations for those messages silently find no matching ID (line ~73)

---

## `src/bridge/gateway/router.py`

- [ ] 🟢 **Duplicate channel mapping silently overwrites** — two config entries with the same Discord channel ID produce only a WARNING log; the first mapping is lost with no hard error (lines ~103–110)

---

## `src/bridge/identity/dev.py`

- [ ] 🟡 **Nick suffix collision** — `discord_to_irc` falls back to `atl_dev_{discord_id[-8:]}` (last 8 hex digits); two users with matching ID suffixes map to the same nick, silently overwriting each other's IRC identity (lines ~87–92)

---

## `src/bridge/identity/portal.py`

- [ ] 🟡 **Circuit breaker check-then-act race** — the check `_consecutive_failures >= threshold` and the read of `_circuit_open_until` are separate non-atomic operations; two concurrent requests can both pass the cooldown gate simultaneously (lines ~129–142)

---

## Verified clean files ✅

Every file below was read in full during the second-pass audit and contains no known issues.

- ✅ `src/bridge/__init__.py`
- ✅ `src/bridge/errors.py`
- ✅ `src/bridge/events.py`
- ✅ `src/bridge/adapters/base.py`
- ✅ `src/bridge/adapters/irc/throttle.py`
- ✅ `src/bridge/adapters/xmpp/media.py`
- ✅ `src/bridge/config/__init__.py`
- ✅ `src/bridge/core/constants.py`
- ✅ `src/bridge/core/errors.py`
- ✅ `src/bridge/core/events.py`
- ✅ `src/bridge/formatting/converter.py`
- ✅ `src/bridge/formatting/discord_to_xmpp.py`
- ✅ `src/bridge/formatting/irc_codes.py`
- ✅ `src/bridge/formatting/markdown.py`
- ✅ `src/bridge/formatting/mention_resolution.py`
- ✅ `src/bridge/formatting/paste.py`
- ✅ `src/bridge/formatting/primitives.py`
- ✅ `src/bridge/formatting/reply_fallback.py`
- ✅ `src/bridge/formatting/xmpp_styling.py`
- ✅ `src/bridge/gateway/bus.py`
- ✅ `src/bridge/gateway/pipeline.py`
- ✅ `src/bridge/gateway/steps.py`
- ✅ `src/bridge/identity/base.py`
- ✅ `src/bridge/identity/sanitize.py`
- ✅ `src/bridge/tracking/base.py`
- ✅ `src/bridge/tracking/message_ids.py`

---

## Summary

| Severity | Count |
|----------|-------|
| 🔴 HIGH  | 4     |
| 🟡 MEDIUM | 38   |
| 🟢 LOW   | 13   |
| **Total** | **55** |

### Corrections from second pass

- **REMOVED** (wrong): `xmpp/handlers.py` delay plugin claim — `get_plugin("delay", check=True)` correctly returns `None` when absent, so the truthiness check is safe
- **ADDED** `config/schema.py` — YAML string `"false"` coerces to `True`
- **ADDED** `formatting/splitter.py` — UTF-8 boundary heuristics
- **ADDED** `identity/dev.py` — nick suffix collision
- **ADDED** `identity/portal.py` — circuit breaker non-atomic check
- **ADDED** `adapters/discord/reply_emoji.py` — hardcoded asset path
- **ADDED** `adapters/xmpp/avatar.py` — broad exception catch
- **ADDED** `avatar.py` — broad exception catch
- **CLARIFIED** `adapters/irc/adapter.py` — only lines ~72, ~76, ~80 are untracked; line ~85 tasks are correctly tracked

### Files by issue count

| File | Issues |
|------|--------|
| `adapters/irc/client.py` | 5 |
| `adapters/discord/adapter.py` | 4 (2 🔴) |
| `adapters/discord/media.py` | 4 (1 🔴) |
| `adapters/irc/handlers.py` | 4 |
| `adapters/xmpp/msgid.py` | 2 |
| `adapters/xmpp/component.py` | 2 |
| `adapters/xmpp/adapter.py` | 2 |
| `adapters/irc/puppet.py` | 2 |
| `adapters/irc/msgid.py` | 2 |
| `gateway/relay.py` | 2 |
| `gateway/msgid_resolver.py` | 2 |
| `config/loader.py` | 2 |
