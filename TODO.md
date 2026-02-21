# TODO

# Bridge Features & Ideas Checklist

Check the boxes `[x]` for the features you want to include in the bridge. Once you are done, let me know and we will generate a new plan based on your selections.

**Legend:** `[x]` = wanted · `[~]` = partially implemented · `[ ]` = not started · `[-]` = not wanted

## 1. Reliability & Connection Management
- [~] **IRC Flood Control / Rate Limiting:** Token bucket algorithm to queue messages and prevent server drops.
- [~] **IRC Rate Limiting Configuration:** Support configuration options like `SendLimit` and `SendBurst`.
- [~] **Exponential Backoff Reconnection:** Reconnect to servers with increasing delays (and jitter) on network issues.
- [-] **Linear Reconnect Backoff:** Simple linear alternative (e.g., 10s, 20s, 30s) instead of exponential.
- [~] **Auto-Rejoin Logic:** Automatically attempt to rejoin IRC/XMPP channels after a `KICK`, disconnect, or ping timeout.
- [ ] **Connection Limiting:** Hard limits on total active IRC connections to prevent resource exhaustion.
- [~] **Ready Detection (PING/PONG):** Wait for `005 ISUPPORT` and a PONG response before processing messages.
- [ ] **Random IPv6 Host Selection:** Randomly pick from available IPv6 addresses for IRC servers to distribute connection load.
- [~] **Send Lock for Race Conditions:** Use `asyncio.Lock()` to serialize message sends to APIs.
- [x] **Message Queue with Delay:** Queue Discord webhook sends with configurable fixed delays to ensure strict order.
- [-] **Fixed Delay Between Messages:** Sleep before/after sending messages (simplistic rate limit).
- [~] **Async Event for Join Coordination:** Use `asyncio.Event` to prevent duplicate concurrent joins to the same channel.
- [ ] **Exit on Send Error:** Configurable behavior to exit the bridge or continue on send errors.

## 2. Security & Moderation
- [x] **AllowedMentions Configuration:** Disable `@everyone` and `@here` (and optionally role mentions) by default in Discord to prevent abuse.
- [ ] **Permission-Based Channel Joining:** Ensure IRC puppets only join channels they have permission to read/write in on Discord.
- [ ] **WebIRC Support:** Use `WEBIRC` on the IRC server so puppets show real IPs/hostnames instead of the bridge's IP.
- [ ] **Allowed/Ignored User Lists:** Whitelist or blacklist specific Discord users from being bridged.
- [ ] **IRC Hostmask Filtering:** Ignore IRC users matching specific glob patterns.
- [~] **Message Content Filtering:** Ignore Discord/IRC messages matching regex patterns.
- [ ] **Message Edit/Delete Logging:** Log all edited and deleted messages to a dedicated moderation channel with before/after comparisons.
- [~] **SASL Authentication:** Use SASL PLAIN/CAP negotiation for IRC authentication instead of standard `NickServ IDENTIFY`.
- [x] **Bot Message Filtering:** Configurable `allowBots` flag to skip bridging messages from other bots (check webhook_id/application_id).
- [ ] **Allowed Speakers Role:** Only bridge messages from Discord users who possess a specific role.

## 3. Messaging & Formatting (Bidirectional)
- [~] **Advanced Discord Markdown Parser:** Use an AST-based parser to properly convert Discord formatting to IRC.
- [~] **IRC Formatting to Discord Markdown:** State-machine parser to convert IRC control codes to Discord markdown.
- [-] **Sophisticated IRC->Discord Formatting (Intervals):** Use bitwise flags and intervals to correctly handle overlapping/nested IRC formatting.
- [~] **URL-Aware Formatting:** Preserve formatting characters (like `_` or `*`) inside URLs so links aren't broken.
- [ ] **Custom Format Strings:** Template-based message formatting (e.g., `<{$displayUsername}> {$text}`).
- [~] **IRC Message Splitting:** Intelligently split long messages into multiple IRC messages (max 512 bytes) at word boundaries.
- [~] **Message Length Truncation:** Truncate messages over 1900 chars for Discord APIs if not splitting.
- [ ] **Multi-line Message Handling:** Split Discord messages by newlines and send each line as a separate IRC message.
- [~] **Automatic Paste Service:** Automatically upload extremely long messages (or multi-line code blocks) to a pastebin service.
- [x] **Reply Tracking & Fallback Chain:** Track cross-platform replies bidirectional. Fallback: cross-platform cache -> same-platform cache -> API fetch.
- [~] **Link Buttons for Replies:** Use Discord UI link buttons to display "Replying to..." context compactly.
- [ ] **Reply vs Forward Detection:** Distinguish between replies and forwarded messages, formatting forwards with source context.
- [ ] **Discord Thread Support:** Bridge Discord threads to XMPP threads (XEP-0201) or specific IRC topics/channels.
- [ ] **Topic Synchronization:** Sync the IRC topic or Discord channel topic with the XMPP MUC subject.
- [ ] **Private Message Support:** Bridge PMs between XMPP/IRC users and Discord users.
- [ ] **Auto-Creating PM Channels:** Dynamically create a Discord channel for each IRC private message (query window).

## 4. Mentions & Anti-Ping
- [ ] **Zero-Width Space (ZWS) Anti-Ping:** Insert `\u200B` in nicknames to prevent accidental highlighting.
  - [ ] *Variant A:* Insert after the first character.
  - [ ] *Variant B:* Insert after vowels for more natural breaking.
  - [ ] *Variant C:* Use Unicode grapheme segmentation.
- [ ] **Strip Anti-Ping Characters:** Remove zero-width spaces when bridging back to Discord.
- [-] **Cyrillic Substitution Anti-Ping:** Replace Latin characters (like `a`, `o`, `e`) with identical-looking Cyrillic characters.
- [ ] **Smart Nick Sanitization (Textual algorithm):** Detect word boundaries and `[nick]` syntax to only allow intentional pings.
- [~] **Cross-Platform Mention Conversion:** Convert Discord `<@id>` to IRC `@nickname`, and IRC `@nickname` to Discord `<@id>`.
- [~] **Markdown Escaping for IRC Nicks:** Escape Discord markdown characters in IRC nicknames so they don't break formatting.
- [~] **IRC Nickname Normalization:** Replace conflicting characters (`!` to `ǃ`, `@` to `＠`) in nicknames.
- [~] **Max Nick Length / Truncation:** Enforce configurable max nickname lengths (e.g., 30 chars).
- [~] **Nickname Suffix and Separator:** Configure fixed suffixes (e.g. `[d]` or `_d`) for bridged nicknames.
- [x] **Nick Length Validation:** Ensure webhook usernames are strictly 2-32 chars (pad short ones, truncate long ones).
- [-] **Username Truncation with Discriminator:** Truncate appropriately while keeping the old #discriminator logic if needed.

## 5. Media, Embeds & Avatars
- [x] **Webhook Avatar Caching with TTL:** Cache Discord avatar URLs with a Time-To-Live to avoid hitting rate limits.
- [~] **Avatar Fallback - Hash-based Colors:** Generate deterministic UI Avatars (`ui-avatars.com`) based on a hash of the IRC user's name.
- [-] **Avatar Fallback - Robohash:** Generate random Robohash avatars for IRC users.
- [x] **Auto-Detect Avatar from Discord:** When an IRC user speaks, search Discord for a matching nickname and use their avatar.
- [ ] **Configurable Avatar URL Template:** Allow user config to define the avatar URL format string.
- [~] **Embed Translation & Extraction:** Extract media (like Tenor GIFs) from embeds and bridge them as raw URLs/attachments.
- [ ] **Embed Suppression:** Use `suppress_embeds=True` on Discord to prevent URL previews.
- [~] **Embed Count Indicator:** Append "(N embeds)" text to messages containing embeds.
- [ ] **Media Link Embedding:** Send standalone media URLs (images/videos) on a separate line so Discord embeds them nicely.
- [x] **XMPP VCard Avatars:** Fetch avatar hashes and images via XMPP VCards for bridged users.
- [ ] **Avatar Dominant Color Extraction:** Extract dominant color from avatar to use in Discord webhook embeds.
- [ ] **Attachment URL Appending:** Append uploaded file URLs to the end of the text message.

## 6. Puppets & Multi-Presence
- [~] **Puppet Lifecycle / Idle Timeout:** Disconnect IRC puppets after a period of inactivity (e.g., 24-48 hours).
- [ ] **Puppet Keep-Alive (Pinger):** Periodically send a `PING` from idle puppets to keep their connection alive.
- [~] **Nickname Collision & Reclaim:** Append `[d]`, `[1]`, `_` on nick collisions, and attempt to reclaim the original nick after a netsplit.
- [ ] **Nick Change Handling:** Detect IRC nick changes and propagate presence updates/renames across the bridge.
- [ ] **AFK/UNAFK Status Sync:** Sync Discord's online/idle/dnd status with IRC's `AWAY` status.
- [-] **IPv6 CIDR Range Puppets:** Assign a deterministic, unique IPv6 address to every puppet to bypass IRC connection limits (Requires infra setup).

## 7. IRC-Specific Features (IRCv3, Modes, Commands)
- [x] **IRCv3 Base Caps (message-tags, message-ids, echo-message):** Negotiate foundation caps required for reply, react, and redaction.
- [~] **IRCv3 Replies (+draft/reply):** Use IRCv3 client tags to track exact message replies bidirectionally.
- [ ] **IRCv3 Message Deletion (draft/message-redaction, REDACT):** Sync deleted messages bidirectionally using the IRCv3 `REDACT` command.
- [ ] **IRCv3 Reactions (+draft/react):** Sync message reactions (emojis) bidirectionally using IRCv3 tags.
- [ ] **IRCv3 Typing Notifications:** Show typing indicators between platforms.
- [~] **IRC Action (/me) Handling:** Detect CTCP `ACTION` and bridge to Discord as italicized `* username action *`.
- [ ] **Auto-Send Pre-Join Commands:** Send automated commands (like `MODE +D` or NickServ commands) immediately upon connecting.
- [ ] **CTCP VERSION / SOURCE Responses:** Automatically respond to IRC CTCP requests with bridge info.
- [ ] **BOT Mode Auto-Detection:** Read `005 ISUPPORT` and automatically set `+B` mode on the connection.
- [ ] **No-Prefix Regex for Bot Commands:** Allow specific messages (like `.help`) to bridge without the `<Username>` prefix.
- [ ] **Channel Keys:** Support joining password-protected IRC channels.
- [ ] **Strip IRC Colors:** Provide a config toggle to strip all color codes from IRC messages completely.
- [ ] **Color-Coded Nicknames:** Assign consistent IRC colors to bridged user nicknames based on a hash of their name or Discord role color.
- [ ] **Room Name Validation:** Validate IRC channels strictly start with `#` or standard prefixes.
- [ ] **IRCv3 away-notify:** Support AFK/UNAFK sync via `AWAY` notifications (requires cap).
- [ ] **IRCv3 multiline (draft/multiline):** Send long messages as batched PRIVMSG with line breaks.
- [ ] **IRCv3 channel-context (+draft/channel-context):** Indicate channel context for PM replies.

## 8. XMPP-Specific Features
- [~] **MUC Join History Suppression:** Send `<history maxchars="0"/>` when joining a MUC to avoid flooding the bridge with backlog.
- [ ] **XMPP Stanza-ID Tracking:** Track messages using the `<stanza-id>` element for exact deduplication.
- [ ] **BOSH / WebSockets Support:** Support for connecting to XMPP over BOSH or WebSockets for better firewall bypassing.
- [-] **Server-to-Server (s2s) Connections:** Support federated bridging using XMPP s2s protocol instead of just c2s.
- [x] **XMPP Stream Management:** Use XEP-0198 to provide session resumption and reliability for XMPP connections.

## 9. Architecture, Storage & Performance
- [~] **Message Cache Backup / Persistence:** Save the message ID mapping cache to disk (compressed JSON) on shutdown so edits/deletes still work after a restart.
- [ ] **Message ID Store for Webhook Edits:** Use `PATCH` with stored Discord message IDs to natively edit webhook messages.
- [ ] **SQLite Persistence:** Use SQLite for dynamic channel mappings, logs, and user configurations.
- [ ] **Compressed JSON Storage:** Use `compress_json` for storing caches efficiently.
- [~] **Webhook Cache Store:** Maintain an in-memory cache of fetched webhooks per server.
- [-] **Guild Member Lazy Loading:** Fetch guild members on-demand (and cache them) rather than syncing huge guilds on startup.
- [~] **Message Echo Prevention:** Use a set/cache of recently sent message IDs to ignore self-messages.
- [ ] **Performance Optimizations:** Integrate `ujson`, `uvloop`, or `aiomultiprocess` for faster bridging throughput.
- [ ] **Hot-Reloadable Configuration:** Reload channel mappings and settings automatically without restarting.
- [ ] **Built-in Upgrader:** Automatic configuration file migrations and update checking.
- [ ] **Mutator / Middleware Pattern:** Message processing pipeline with lifecycle control (`CONTINUE`, `STOP`, `DISCARD`).
- [ ] **Message Parts Architecture:** Treat messages as objects of distinct parts (text, mentions, actions) rather than flat strings.
- [-] **Pluggable Architecture:** Support loading external plugins for new protocols or features.
- [ ] **Queue-Based Command Processing:** Separate threads/queues for processing Discord, IRC, puppet events.
- [~] **Event Dispatcher Pattern:** Central event dispatcher with graceful error handling per target.
- [ ] **Silent Message Sending:** Support internal methods to send messages silently without triggering further events (prevent loops).

## 10. UI/UX, Analytics & Logging
- [ ] **Deduplication Emojis:** Add visual indicators (colored square emojis) to show when messages have been deduplicated.
- [ ] **Emoji Limit for Spam Prevention:** Restrict the maximum number of custom emojis rendered per message to prevent spam.
- [ ] **Statistics & Uptime Tracker:** Track total bridged messages per direction and uptime.
- [ ] **Prometheus Metrics Integration:** Expose prometheus metrics for monitoring.
- [ ] **Welcome/Goodbye Messages:** Send customizable template messages when users join or leave the bridged channels.
- [~] **Bridge Member Changes (Join/Part/Quit):** Bridge connect/disconnect events across platforms as text messages.
- [~] **Configurable Event Logging:** Let admins toggle logging of JOIN/PART/QUIT events per platform.
- [ ] **HTTP Server for Log Viewing:** Expose a web UI for viewing SQLite message logs.
- [ ] **User Command History Tracking:** Log admin commands specifically for debugging.

## 11. Testing & Tooling
- [~] **Mock Discord Backend for Tests:** Implement fake connection states and HTTP clients to run unit tests without hitting APIs.
- [~] **Factory Pattern for Test Fixtures:** Create realistic test objects (Messages, Users, Attachments) using factories.
- [ ] **Async Event Runner for Tests:** Ensure all async events are awaited properly to prevent race conditions during test execution.
- [ ] **Fluent Assertion API (Verify Pattern):** Chainable test assertions (e.g. `verify().message().content("x")`).
- [ ] **Message Queue for Sent Messages:** Track sent messages in tests with peek capabilities.
- [ ] **Error Queue for Command Errors:** Specific queue in tests to track and verify caught exceptions.
- [~] **Pytest Fixtures for Bot Setup:** Auto-setup bot instances per test.
- [ ] **Attachment Factory:** Generate mock attachments for testing.
- [ ] **Configuration Decorator:** Enforce test configuration state via decorators.


## High Priority (Reliability)

### IRC Flood Control
**Status:** Not implemented
**Priority:** High
**Source:** Matterbridge audit, Biboumi audit

**What it does:**
- Message queue with configurable delay between sends
- Prevents rate limiting and connection drops
- Token bucket algorithm for rate limiting

**Biboumi implementation:**
- Token bucket: 1 token per second refill
- Default limit: 10 messages
- Messages queued when tokens exhausted
- Per-server configurable limit
- Can bypass throttling for critical messages (PING/PONG)

**Implementation:**
```python
# Add to IRC adapter
class TokenBucket:
    def __init__(self, limit: int, refill_rate: float = 1.0):
        self.limit = limit
        self.tokens = limit
        self.refill_rate = refill_rate
        self.last_refill = time.time()
    
    def use_token(self) -> bool:
        self._refill()
        if self.tokens > 0:
            self.tokens -= 1
            return True
        return False
    
    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.limit, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

# In IRC adapter
message_queue: asyncio.Queue
tokens_bucket: TokenBucket
```

**Config:**
```yaml
irc_throttle_limit: 10  # messages per second
irc_message_queue: 30   # max queue size
```

### IRC Rejoin Logic
**Status:** Not implemented
**Priority:** High
**Source:** Matterbridge audit, Biboumi audit

**What it does:**
- Automatic rejoin after KICK
- Automatic rejoin on disconnect/ping timeout
- Configurable rejoin delay

**Biboumi status:**
- Tracks channels to join but NO automatic rejoin after KICK
- Marks channel as not joined but doesn't attempt rejoin
- Opportunity for improvement over biboumi

**Implementation:**
```python
async def handle_kick(self, channel: str, reason: str):
    # Don't rejoin if banned
    if "ban" in reason.lower():
        return
    
    await asyncio.sleep(self.rejoin_delay)
    await self.join(channel)

async def on_disconnect(self):
    # Rejoin all channels we were in
    for channel in self.joined_channels:
        await asyncio.sleep(self.rejoin_delay)
        await self.join(channel)
```

**Config:**
```yaml
irc_rejoin_delay: 5  # seconds
irc_auto_rejoin: true
```

### Nick Sanitization
**Status:** Not implemented
**Priority:** High
**Source:** Matterbridge audit

**What it does:**
- Sanitize Discord usernames for IRC compatibility
- Replace special characters (@#:/) with safe alternatives
- Prevent IRC command injection

**Biboumi status:**
- Not needed in biboumi (uses XMPP JIDs, not Discord usernames)
- ATL Bridge needs this due to puppet model using Discord names directly

**Implementation:**
```python
def sanitize_nick(nick: str) -> str:
    # Remove/replace IRC special chars
    nick = re.sub(r'[@#:/\\]', '-', nick)
    # Truncate to IRC nick limit (typically 9-30 chars)
    nick = nick[:30]
    # Strip/transliterate Unicode/emoji
    nick = unicodedata.normalize('NFKD', nick).encode('ascii', 'ignore').decode()
    return nick or "user"  # fallback if empty
```

### Connection Backoff
**Status:** Partial (Portal client has retry)
**Priority:** High
**Source:** Matterbridge audit, Biboumi audit

**What it does:**
- Exponential backoff for IRC/XMPP reconnects
- Prevents connection spam on network issues
- Configurable min/max backoff times

**Biboumi implementation:**
- Fixed 2-second delay for XMPP reconnection
- Port fallback for IRC (tries next port on failure)
- No exponential backoff or jitter
- No max retry limit

**Implementation:**
```python
from tenacity import retry, wait_exponential

**Implementation:**
```python
from tenacity import retry, wait_exponential, stop_after_attempt
import random

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(10)
)
async def connect(self):
    # Add jitter to prevent thundering herd
    jitter = random.uniform(0.5, 1.5)
    await asyncio.sleep(jitter)
    ...
```

## Medium Priority (Features)

### IRC Channel Keys
**Status:** Not implemented
**Priority:** Medium
**Source:** Matterbridge audit, Biboumi audit

**What it does:**
- Support password-protected IRC channels
- Per-channel key configuration

**Biboumi implementation:**
- Full support with batched JOIN commands
- Handles multiple channels with different keys
- Proper error handling (475 ERR_BADCHANNELKEY)
- Sends: `JOIN #chan1,#chan2 key1,key2`

**Config:**
```yaml
mappings:
  - discord_channel_id: "123"
    irc:
      server: "irc.libera.chat"
      channel: "#private"
      key: "password123"
```

**Implementation:**
```python
# Store keys securely, handle 475 numeric
async def join_channel(self, channel: str, key: str = ""):
    if key:
        await self.send(f"JOIN {channel} {key}")
    else:
        await self.send(f"JOIN {channel}")
```

### SASL Authentication
**Status:** Not implemented (using NickServ IDENTIFY)
**Priority:** Medium
**Source:** Matterbridge audit, Biboumi audit

**What it does:**
- More secure IRC authentication
- No password in plaintext IDENTIFY command
- Alternative to NickServ

**Biboumi implementation:**
- Full SASL PLAIN support with CAP negotiation
- Graceful fallback on failure
- Per-server credential storage
- State machine: unneeded → needed → success/failure

**CAP negotiation flow:**
1. Send `CAP REQ :sasl`
2. Server responds `CAP ACK :sasl`
3. Send `AUTHENTICATE PLAIN`
4. Server responds `AUTHENTICATE +`
5. Send base64(`\0username\0password`)
6. Server responds `903` (success) or `904` (failure)
7. Send `CAP END`

**Config:**
```yaml
irc_use_sasl: true
irc_sasl_user: "username"
irc_sasl_password: "password"
```

### Verbose Join/Part
**Status:** Partial (basic join/part)
**Priority:** Low
**Source:** Matterbridge audit

**What it does:**
- Include ident@host in presence messages
- More detailed join/part notifications

**Config:**
```yaml
verbose_join_part: true  # "user (ident@host) joins"
```

## Future XEP Implementations

### XEP-0394: Message Markup
**Status:** Deferred - needs investigation

**What it does:**
- Semantic markup for bold, italic, code, quotes, lists
- Uses character position ranges instead of Markdown syntax
- Example: `<span start="6" end="11"><emphasis/></span>` for bold text

**Why deferred:**
- Complex bidirectional conversion between Discord Markdown and positional markup
- Requires parsing `**bold**`, `*italic*`, `` `code` ``, `> quote` and calculating offsets
- Breaks on edits (positions shift)
- Most XMPP clients already render Markdown
- High implementation complexity for marginal UX improvement

**Implementation notes if revisited:**
- Need robust Markdown parser for Discord → XMPP
- Need to reconstruct Markdown from position spans for XMPP → Discord
- Handle nested formatting, Unicode, emojis correctly
- Consider using existing Markdown library (e.g., `markdown-it-py`)
- Test with complex messages (mixed formatting, mentions, links)

**Dependencies:**
- `xep_0030` (Service Discovery)
- `xep_0071` (XHTML-IM) - deprecated, may need alternative approach

---

## Biboumi Audit Findings

**Date:** 2026-02-19
**Source:** [biboumi](https://github.com/louiz/biboumi) - C++ IRC-XMPP gateway

### Features Biboumi Has (We Can Learn From)

1. **✅ IRC Flood Control** - Token bucket with 1 token/second refill
   - Configurable per-server limit (default: 10)
   - Automatic message queuing
   - Can bypass for critical messages

2. **✅ SASL Authentication** - Full CAP negotiation + SASL PLAIN
   - State machine implementation
   - Graceful fallback on failure
   - Per-server credentials

3. **✅ IRC Channel Keys** - Password-protected channels
   - Batched JOIN commands
   - Proper error handling (475 numeric)

4. **✅ IRC Color Formatting** - IRC codes → XHTML-IM
   - Supports bold, italic, underline, colors
   - Non-hierarchical span approach

5. **⚠️ Connection Backoff** - Fixed 2s delay (not exponential)
   - Port fallback for IRC
   - No jitter or max retry limit

6. **⚠️ IRC Rejoin Logic** - Tracks channels but no auto-rejoin
   - Marks as not joined after KICK
   - Doesn't attempt rejoin

### Implementation Priorities from Biboumi

**Immediate (High Priority):**
1. IRC Flood Control - Token bucket (~2-3 hours)
2. IRC Rejoin Logic - Auto-rejoin after KICK (~1 hour)
3. Connection Backoff - Exponential with jitter (~30 min)

**Short-term (Medium Priority):**
4. SASL Authentication - CAP negotiation (~4-5 hours)
5. IRC Channel Keys - Config addition (~1 hour)

**Long-term (Low Priority):**
6. IRC Color Formatting - Basic conversion (~6-8 hours)

**Total estimated effort:** 15-20 hours for all high/medium priority features

### Code Quality Observations

**Strengths:**
- Robust error handling for every IRC numeric
- Database-driven per-server config
- Modular design (IRC/XMPP/bridge separation)
- Comprehensive test suite (16 test files)

**Weaknesses:**
- C++ complexity (memory management)
- Fixed delays (no exponential backoff)
- Limited documentation
- No metrics/monitoring

**Lessons for ATL Bridge:**
- Use database/Portal for per-server config
- Implement error handlers for all IRC numerics
- Add metrics from the start
- Keep Python's async/await simplicity advantage

---

## Slidcord Implementation Patterns

**Date:** 2026-02-19
**Source:** [slidcord](https://codeberg.org/nicoco/slidcord) - Python Discord-XMPP gateway (slidge-based)

### Implementation Patterns to Adopt

1. **✅ Message Echo Prevention**
   - Track sent message IDs in `ignore_next_msg_event` set
   - Prevents duplicate messages from own sends
   - Implementation: `self.ignore_next_msg_event.add(msg.id)` before send
   - **Status:** We already handle this differently (check author ID)

2. **✅ Send Lock for Race Conditions**
   - Use `asyncio.Lock()` to serialize message sends
   - Prevents interleaved messages and API race conditions
   - Implementation:
     ```python
     self.send_lock = asyncio.Lock()
     async with self.send_lock:
         msg = await channel.send(text)
     ```
   - **Priority:** Medium - Add to Discord adapter
   - **Effort:** 30 minutes

3. **✅ Guild Member Lazy Loading**
   - Fetch guild members on-demand with lock
   - Cache fetched guild IDs to prevent duplicate fetches
   - Rate limiting awareness (don't fetch for large guilds by default)
   - Implementation:
     ```python
     self.guild_members_fetch_lock = asyncio.Lock()
     self.guild_members_fetched: set[int] = set()
     
     async with self.guild_members_fetch_lock:
         if guild.id not in self.guild_members_fetched:
             await guild.fetch_members(cache=True)
             self.guild_members_fetched.add(guild.id)
     ```
   - **Priority:** Low - We use webhooks, don't need full member list
   - **Effort:** 1 hour if needed

4. **⚠️ Discord Thread Support**
   - Map Discord threads to XMPP threads
   - Handle thread creation/rename events
   - Thread-aware message routing
   - **Status:** Not implemented
   - **Priority:** Medium - Useful for busy channels
   - **Effort:** 3-4 hours
   - **Implementation notes:**
     - Store thread_id in MessageIn/MessageOut events
     - IRC: Use thread name as channel topic or separate channel
     - XMPP: Use XEP-0201 (Best Practices for Message Threads)

5. **✅ Embed Extraction**
   - Extract Tenor GIFs from Discord embeds
   - Send as attachments instead of URLs
   - Implementation:
     ```python
     for embed in message.embeds:
         if embed.provider.name == "Tenor":
             attachments.append(Attachment(url=embed.video.url))
     ```
   - **Priority:** Low - Nice-to-have
   - **Effort:** 1 hour

6. **✅ Reply vs Forward Detection**
   - Distinguish between Discord replies and forwarded messages
   - Format forwarded messages with source context
   - Implementation:
     ```python
     if message.type != MessageType.reply and reply_to is not None:
         # This is a forwarded message
         text = f"↱ Forwarded from {source}\n> {quoted_text}"
     ```
   - **Priority:** Low - Edge case
   - **Effort:** 2 hours

7. **✅ Rate Limiting Awareness**
   - Don't auto-fetch profiles for non-friends (triggers rate limits)
   - Configurable member fetching for large guilds
   - Graceful degradation when rate limited
   - **Priority:** Medium - Important for large servers
   - **Effort:** Already handled by discord.py rate limiting

### Recommended Additions to ATL Bridge

**Immediate:**
- Add send lock to Discord adapter (30 min)

**Short-term:**
- Discord thread support (3-4 hours)
- Embed extraction for Tenor GIFs (1 hour)

**Long-term:**
- Reply vs forward detection (2 hours)
- Guild member lazy loading if needed (1 hour)

**Total estimated effort:** 5-6 hours for immediate + short-term features

---

## Black-Hole Implementation Patterns

**Date:** 2026-02-19
**Source:** [black-hole](https://github.com/slice/black-hole) - Python XMPP-Discord bridge

### Implementation Patterns to Adopt

1. **✅ Message Queue with Delay**
   - Queue XMPP→Discord messages to preserve order
   - Configurable delay between webhook sends (default: 0.25s)
   - Background consumer processes queue with `asyncio.Event`
   - Implementation:
     ```python
     self._queue = []
     self._incoming = asyncio.Event()
     
     async def _sender(self):
         while True:
             await self._incoming.wait()
             for job in self._queue:
                 await self.session.post(webhook_url, json=payload)
                 await asyncio.sleep(self.config["delay"])
             self._queue.clear()
             self._incoming.clear()
     ```
   - **Priority:** Medium - Ensures message order
   - **Effort:** 2 hours
   - **Note:** We already use webhooks, this adds ordering guarantee

2. **✅ Avatar Caching with TTL**
   - Cache Discord avatar URLs with timestamp-based invalidation
   - Default: 30 minutes (1800s)
   - Uses `time.monotonic()` for stable timing
   - Prevents rate limiting from repeated avatar fetches
   - Implementation:
     ```python
     self._avatar_cache = {}  # { user_id: (invalidation_ts, avatar_url) }
     
     async def _get_from_cache(self, user_id: int):
         current = time.monotonic()
         cache_period = 30 * 60  # 30 minutes
         invalidation_ts = current + cache_period
         
         value = self._avatar_cache.get(user_id)
         if value is None:
             user = await self.client.fetch_user(user_id)
             avatar_url = str(user.avatar_url_as(format="png"))
             self._avatar_cache[user_id] = (invalidation_ts, avatar_url)
             return avatar_url
         
         user_ts, avatar_url = value
         if current > user_ts:
             self._avatar_cache.pop(user_id)
             return await self._get_from_cache(user_id)
         return avatar_url
     ```
   - **Priority:** High - We already cache avatars, but no TTL
   - **Effort:** 1 hour to add TTL invalidation
   - **Status:** Partial - We have MD5-based cache, add time-based invalidation

3. **✅ Message ID Store for Edits**
   - Store `(jid, xmpp_message_id) -> discord_message_id` mapping
   - Uses `ExpiringDict` with 1-hour TTL and 1000 message limit
   - Enables PATCH webhook for edits instead of new POST
   - Implementation:
     ```python
     from expiringdict import ExpiringDict
     
     self._message_id_store = ExpiringDict(max_len=1000, max_age_seconds=3600)
     
     # On send
     store_key = (author_jid, xmpp_message_id)
     lookup_key = (author_jid, original_xmpp_message_id)
     
     if original_xmpp_message_id and lookup_key in self._message_id_store:
         discord_message_id = self._message_id_store[lookup_key]
         await session.patch(f"{webhook_url}/messages/{discord_message_id}", json=payload)
     else:
         resp = await session.post(webhook_url, json=payload)
         discord_message = await resp.json()
         self._message_id_store[store_key] = discord_message["id"]
     ```
   - **Priority:** High - Better than our current approach
   - **Effort:** 2-3 hours
   - **Status:** We track message IDs but don't use webhook PATCH for edits

4. **✅ Mention Sanitization**
   - Strip/escape @everyone and @here mentions
   - Convert user/role mentions to non-mentioning format
   - Prevents mention abuse from XMPP side
   - Implementation:
     ```python
     def clean_content(content: str) -> str:
         content = content.replace("@everyone", "@\u200beveryone")
         content = content.replace("@here", "@\u200bhere")
         content = re.sub(r"<@[!&]?(\d+)>", lambda m: m.group(0).strip("<>"), content)
         return content
     ```
   - **Priority:** High - Security/anti-abuse
   - **Effort:** 30 minutes
   - **Status:** Not implemented

5. **✅ Nick Length Validation**
   - Ensure webhook usernames are 2-32 characters
   - Pad short nicks: `<x>` for single-char nicks
   - Truncate long nicks to 32 chars
   - Implementation:
     ```python
     def ensure_valid_nick(nick: str) -> str:
         if len(nick) < 2:
             return f"<{nick}>"
         if len(nick) > 32:
             return nick[:32]
         return nick
     ```
   - **Priority:** Medium - Prevents webhook errors
   - **Effort:** 15 minutes
   - **Status:** Not implemented

6. **✅ Message Length Truncation**
   - Truncate messages over 1900 chars with "... (trimmed)"
   - Prevents Discord API errors (2000 char limit)
   - Implementation:
     ```python
     if len(content) > 1900:
         content = content[:1900] + "... (trimmed)"
     ```
   - **Priority:** Medium - Better than silent failure
   - **Effort:** 15 minutes
   - **Status:** Not implemented (we should split instead)

7. **✅ Attachment URL Appending**
   - Append attachment URLs to message content
   - Simple approach: just add URLs separated by spaces
   - Implementation:
     ```python
     if message.attachments:
         urls = " ".join(attachment.proxy_url for attachment in message.attachments)
         content += " " + urls
     ```
   - **Priority:** Low - We already handle attachments better
   - **Effort:** N/A
   - **Status:** We use proper file uploads

8. **✅ Embed Count Indicator**
   - Add "(N embeds)" to message when embeds present
   - Simple notification that embeds exist
   - Implementation:
     ```python
     if message.embeds:
         s = "" if len(message.embeds) == 1 else "s"
         content += f" ({len(message.embeds)} embed{s})"
     ```
   - **Priority:** Low - Nice-to-have
   - **Effort:** 15 minutes

### Recommended Additions to ATL Bridge

**Immediate (High Priority):**
1. Mention sanitization - Prevent @everyone/@here abuse (30 min)
2. Avatar cache TTL - Add time-based invalidation (1 hour)
3. Message ID store for webhook edits - Use PATCH instead of new messages (2-3 hours)

**Short-term (Medium Priority):**
4. Message queue with delay - Preserve message order (2 hours)
5. Nick length validation - Prevent webhook errors (15 min)
6. Message length handling - Split or truncate (30 min)

**Long-term (Low Priority):**
7. Embed count indicator (15 min)

**Total estimated effort:** 6-8 hours for immediate + short-term features

### Key Insights from Black-Hole

**Strengths:**
- Simple, focused implementation (8 files, ~500 LOC)
- Effective use of asyncio primitives (Event, Queue pattern)
- Smart caching with TTL to avoid rate limits
- Webhook PATCH for edits (better than reposting)

**Weaknesses:**
- No retry logic or error recovery
- Truncates long messages instead of splitting
- No IRC support (XMPP-Discord only)
- Limited XEP support

**Best practices to adopt:**
- Use `time.monotonic()` for cache invalidation (more stable than `time.time()`)
- Queue messages with delay for ordering guarantees
- PATCH webhook messages for edits (requires storing webhook URL + message ID)
- Sanitize mentions before sending to Discord

---

## Revcord Implementation Patterns

**Date:** 2026-02-19
**Source:** [revcord](https://github.com/mayudev/revcord) - TypeScript Discord-Revolt bridge

### Implementation Patterns to Adopt

1. **✅ Cross-Platform Reply Tracking**
   - Separate caches for each direction: `discordCache` and `revoltCache`
   - Track original message ID, author, created message ID, channel
   - Enables cross-platform reply threading
   - Implementation:
     ```python
     @dataclass
     class CachedMessage:
         parent_message: str  # Original message ID
         parent_author: str   # Original author ID
         created_message: str # Bridged message ID
         channel_id: str      # Channel ID
     
     discord_cache: list[CachedMessage] = []
     xmpp_cache: list[CachedMessage] = []
     
     # When bridging reply from Discord to XMPP
     cross_platform_ref = next(
         (c for c in xmpp_cache if c.created_message == reply_to_id),
         None
     )
     if cross_platform_ref:
         # Reply to the original XMPP message
         reply_to = cross_platform_ref.parent_message
     ```
   - **Priority:** High - Enables proper reply threading
   - **Effort:** 2-3 hours
   - **Status:** We track message IDs but not bidirectionally

2. **✅ Reply Fallback Chain**
   - Try cross-platform cache first
   - Fall back to same-platform cache
   - Final fallback: fetch message from API
   - Graceful degradation if fetch fails
   - Implementation:
     ```python
     # 1. Check cross-platform cache
     cross_ref = find_in_cache(other_platform_cache, reply_id)
     if cross_ref:
         return cross_ref.parent_message
     
     # 2. Check same-platform cache
     same_ref = find_in_cache(same_platform_cache, reply_id)
     if same_ref:
         return same_ref.created_message
     
     # 3. Fetch from API
     try:
         original = await channel.fetch_message(reply_id)
         return format_reply_embed(original)
     except NotFound:
         return "[message not found]"
     ```
   - **Priority:** Medium - Better UX for replies
   - **Effort:** 1-2 hours

3. **✅ Username Truncation with Discriminator**
   - Truncate to 32 chars for webhook usernames
   - Include discriminator only if not new username system
   - Implementation:
     ```python
     def format_username(username: str, discriminator: str) -> str:
         # New username system has discriminator "0"
         if len(discriminator) == 1:
             return username[:32]
         return f"{username}#{discriminator}"[:32]
     ```
   - **Priority:** Low - Discord removed discriminators
   - **Effort:** 15 minutes
   - **Status:** Not needed (Discord changed system)

4. **✅ Embed Translation**
   - Convert Discord embeds to target platform format
   - Only allow embeds from bots (security)
   - Graceful failure if translation fails
   - Implementation:
     ```python
     if message.embeds and message.author.bot:
         try:
             translated_embed = translate_embed(message.embeds[0])
             message_object["embeds"] = [translated_embed]
         except Exception as e:
             log.warning("Failed to translate embed: %s", e)
             # Continue without embed
     ```
   - **Priority:** Medium - Better embed support
   - **Effort:** 3-4 hours
   - **Status:** We extract some embeds (Tenor), not full translation

5. **✅ Attachment URL Concatenation**
   - Append all attachment URLs to message content
   - Simple newline-separated list
   - Implementation:
     ```python
     message_string = content + "\n"
     for attachment in attachments:
         message_string += attachment.url + "\n"
     message_string = message_string.rstrip("\n")
     ```
   - **Priority:** Low - We handle attachments better
   - **Effort:** N/A
   - **Status:** We use proper file uploads

6. **✅ Bot Message Filtering**
   - Configurable per-channel bot message bridging
   - `allowBots` flag in channel mapping
   - Skip messages from own bot application
   - Implementation:
     ```python
     if target and message.application_id != bot.user.id:
         if not message.author.bot or target.allow_bots:
             # Bridge the message
     ```
   - **Priority:** Medium - Prevents bot loops
   - **Effort:** 1 hour
   - **Status:** We check webhook_id, add application_id check

7. **✅ Emoji Limit for Spam Prevention**
   - Limit displayed custom emojis to 5
   - Prevents emoji spam/bombing
   - Implementation:
     ```python
     emojis = re.findall(EMOJI_PATTERN, content)
     for i, emoji in enumerate(emojis):
         if i < 5:  # Limit to 5 emojis
             emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.webp"
             content = content.replace(emoji, f"[:{emoji_name}:]({emoji_url})")
         else:
             content = content.replace(emoji, f":{emoji_name}:")
     ```
   - **Priority:** Low - Anti-spam measure
   - **Effort:** 30 minutes

8. **✅ SQLite Persistence**
   - Store channel mappings in SQLite database
   - Sequelize ORM for easy management
   - Auto-sync schema on startup
   - Implementation:
     ```python
     # Using SQLAlchemy or similar
     class Mapping(Base):
         __tablename__ = "mappings"
         id = Column(Integer, primary_key=True)
         discord_channel = Column(String)
         xmpp_muc = Column(String)
         irc_channel = Column(String)
         allow_bots = Column(Boolean, default=True)
     ```
   - **Priority:** Medium - Better than YAML for dynamic mappings
   - **Effort:** 2-3 hours
   - **Status:** We use YAML config, consider DB for dynamic mappings

### Recommended Additions to ATL Bridge

**Immediate (High Priority):**
1. Cross-platform reply tracking - Bidirectional cache (2-3 hours)
2. Bot message filtering - Add application_id check (1 hour)

**Short-term (Medium Priority):**
3. Reply fallback chain - Better reply handling (1-2 hours)
4. Embed translation - Full embed support (3-4 hours)
5. SQLite persistence - Dynamic channel mappings (2-3 hours)

**Long-term (Low Priority):**
6. Emoji limit - Spam prevention (30 min)

**Total estimated effort:** 9-13 hours for immediate + short-term features

### Key Insights from Revcord

**Strengths:**
- Bidirectional message caching for cross-platform replies
- Graceful fallback chain for reply resolution
- Per-channel bot filtering configuration
- SQLite persistence for dynamic mappings
- Emoji spam prevention

**Weaknesses:**
- No rate limiting or throttling
- No retry logic
- TypeScript (not Python, harder to adapt)
- Revolt-specific (not IRC/XMPP)

**Best practices to adopt:**
- Separate caches for each bridge direction
- Three-tier fallback for reply resolution (cache → cache → API)
- Per-channel configuration flags (allow_bots, etc.)
- Database persistence for dynamic configuration
- Limit custom emoji display to prevent spam

---

## CatPuppetBridge Implementation Patterns

**Date:** 2026-02-19
**Source:** [CatPuppetBridge](https://github.com/hypatia-software-org/CatPuppetBridge) - Python IRC-Discord bridge with puppets

### Implementation Patterns to Adopt

1. **✅ WebIRC Integration**
   - Use WebIRC for enhanced security and proper hostname display
   - Prevents impersonation and shows real Discord user info
   - Implementation:
     ```python
     connection.send_raw(
         f"WEBIRC {password} {hostname} {hostname} {ip_address}"
     )
     ```
   - **Priority:** High - Better security and UX
   - **Effort:** 1-2 hours
   - **Status:** Not implemented - we use standard IRC connection

2. **✅ Permission-Based Channel Joining**
   - Puppets only join channels they have Discord permissions for
   - Dynamic join/part based on role changes
   - Implementation:
     ```python
     async def accessible_channels(self, user_id):
         channels = []
         for channel_id in mapped_channels:
             channel = self.get_channel(channel_id)
             member = channel.guild.get_member(user_id)
             if channel.permissions_for(member).read_messages:
                 channels.append(channel_id)
         return channels
     
     # On role change
     async def on_member_update(self, before, after):
         if before.roles != after.roles:
             channels = await self.accessible_channels(after.id)
             await send_command(after, 'join_part', channels)
     ```
   - **Priority:** High - Respects Discord permissions
   - **Effort:** 2-3 hours
   - **Status:** Not implemented - puppets join all mapped channels

3. **✅ AFK/UNAFK Status Management**
   - Set IRC AWAY status based on Discord presence
   - Automatic AFK when offline/DND, UNAFK when online/idle
   - Implementation:
     ```python
     async def on_presence_update(self, before, after):
         previously_inactive = before.status in (Status.offline, Status.dnd)
         now_active = after.status in (Status.online, Status.idle)
         
         if previously_inactive and now_active:
             await send_irc_command(after, 'unafk')
         elif previously_active and now_inactive:
             await send_irc_command(after, 'afk')
     ```
   - **Priority:** Medium - Nice UX feature
   - **Effort:** 1 hour
   - **Status:** Not implemented

4. **✅ IRC Message Splitting**
   - Calculate reserved bytes for IRC protocol overhead
   - Split at word boundaries when possible
   - Respect 512 byte IRC message limit
   - Implementation:
     ```python
     def msg_reserved_bytes(self, target, nickname, hostname):
         # :<nick>!<nick>@<host> PRIVMSG <target> :\r\n
         msg = f":<{nickname}>!<{nickname}>@<{hostname}> PRIVMSG <{target}> :"
         return len(msg.encode("utf8")) + 4  # +CRLF
     
     def split_irc_message(self, message, target):
         max_bytes = 512 - self.msg_reserved_bytes(target)
         lines = []
         message = re.sub(r'[\r\n]+', '', message)  # Strip newlines
         
         while len(message[:max_bytes]) != 0:
             chunk = message[:max_bytes]
             
             # Don't split mid-word
             if len(chunk) + 1 < len(message):
                 if not (message[len(chunk)] == ' ' or message[len(chunk)-1] == ' '):
                     chunk = chunk.rsplit(" ", 1)[0]
             
             lines.append(chunk)
             message = message[len(chunk):].lstrip()
         return lines
     ```
   - **Priority:** High - Prevents message truncation
   - **Effort:** 2 hours
   - **Status:** Not implemented - we should split instead of truncate

5. **✅ Puppet Lifecycle Management**
   - Activate puppet on first message or presence change
   - Deactivate puppet when user leaves guild
   - Track active puppets in memory
   - Implementation:
     ```python
     active_puppets: set[int] = set()
     
     async def activate_puppet(self, user):
         channels = await self.accessible_channels(user.id)
         await send_irc_command(user, 'active', channels)
         self.active_puppets.add(user.id)
     
     async def on_member_remove(self, member):
         if member.id in self.active_puppets:
             self.active_puppets.remove(member.id)
             await send_irc_command(member, 'die')
     ```
   - **Priority:** Medium - Better resource management
   - **Effort:** 1-2 hours
   - **Status:** Partial - we have idle timeout, not guild leave detection

6. **✅ IRC-Safe Nickname Generation**
   - Strip non-IRC-safe characters
   - Ensure first character is letter or special char
   - Truncate to fit IRC limits with display name + username
   - Implementation:
     ```python
     def irc_safe_nickname(self, nickname: str) -> str:
         allowed_special = r"\[\]\\`_^{|}"
         nickname = nickname.strip()
         
         # First char must be letter or special
         first_char = nickname[0]
         if not re.match(r"[A-Za-z" + allowed_special + "]", first_char):
             nickname = "_" + nickname[1:]
         
         # Remove invalid chars
         valid_nick = re.sub(r"[^A-Za-z0-9" + allowed_special + "]", "", nickname)
         return valid_nick
     
     async def generate_irc_nickname(self, user):
         username = self.irc_safe_nickname(user.name)
         display_name = self.irc_safe_nickname(user.display_name)
         
         # Format: DisplayName[username]_suffix
         reserved = 2 + len(suffix)  # [] + suffix
         max_len = 30
         
         if len(display_name) + len(username) + reserved > max_len:
             # Truncate username first, then display name
             ...
         
         return f"{display_name}[{username}]{suffix}"
     ```
   - **Priority:** High - Prevents IRC errors
   - **Effort:** 1-2 hours
   - **Status:** Partial - we sanitize but not as thoroughly

7. **✅ Exponential Backoff Reconnection**
   - Retry with increasing delays: 10s, 20s, 30s... up to 300s (5 min)
   - Automatic reconnection on disconnect
   - Implementation:
     ```python
     def connect_and_retry(self, server, port, nickname, tls=False):
         retry_count = 1
         while True:
             try:
                 self.connection = self.reactor.server().connect(
                     server, port, nickname, connect_factory=ssl_factory if tls else None
                 )
                 break
             except (ServerConnectionError, TimeoutError):
                 delay = min(10 * retry_count, 300)
                 log.warning('Connection failed %d times, retrying in %ds', retry_count, delay)
                 retry_count += 1
                 time.sleep(delay)
         
         self.connection.add_global_handler("disconnect", self.on_disconnect)
     
     def on_disconnect(self, c, e):
         self.connect_and_retry(self.server, self.port, self.nickname, self.tls)
     ```
   - **Priority:** High - Better reliability
   - **Effort:** 1 hour
   - **Status:** Not implemented - we should add this

8. **✅ Queue-Based Command Processing**
   - Separate queues for different message types
   - Worker threads process queues asynchronously
   - Commands: send, afk, unafk, nick, join_part, send_dm, die
   - Implementation:
     ```python
     queues = {
         'in_queue': Queue(),      # Discord → IRC
         'out_queue': Queue(),     # IRC → Discord
         'puppet_queue': Queue(),  # Puppet commands
         'dm_out_queue': Queue()   # DMs
     }
     
     def process_discord_queue(self):
         for msg in iter(self.queues['in_queue'].get, sentinel):
             match msg['command']:
                 case 'send':
                     self.do_send(msg)
                 case 'afk':
                     self.connection.send_raw("AWAY :Away")
                 case 'unafk':
                     self.connection.send_raw("AWAY")
                 case 'nick':
                     self.connection.nick(msg['irc_nick'])
                 case 'join_part':
                     self.join_part(msg['data'])
                 case 'die':
                     self.end('has left discord')
     ```
   - **Priority:** Medium - Better architecture
   - **Effort:** 3-4 hours
   - **Status:** We use event bus, not queues

9. **✅ Robohash Avatar Generation**
   - Generate random avatars for IRC users without Discord accounts
   - Use robohash.org for consistent avatar generation
   - Implementation:
     ```python
     def get_avatar_url(self, irc_nick, discord_users):
         # Check if IRC nick matches Discord user
         for user in discord_users:
             if user.name.lower() == irc_nick.lower():
                 return user.avatar.url
         
         # Generate robohash avatar
         return f"https://robohash.org/{irc_nick}.png"
     ```
   - **Priority:** Low - Nice-to-have
   - **Effort:** 30 minutes
   - **Status:** We use Portal for avatars

### Recommended Additions to ATL Bridge

**Immediate (High Priority):**
1. WebIRC integration - Better security (1-2 hours)
2. Permission-based channel joining - Respect Discord perms (2-3 hours)
3. IRC message splitting - Proper 512 byte handling (2 hours)
4. IRC-safe nickname generation - Prevent errors (1-2 hours)
5. Exponential backoff reconnection - Better reliability (1 hour)

**Short-term (Medium Priority):**
6. AFK/UNAFK status management - Better UX (1 hour)
7. Puppet lifecycle management - Resource efficiency (1-2 hours)
8. Queue-based command processing - Better architecture (3-4 hours)

**Long-term (Low Priority):**
9. Robohash avatar fallback (30 min)

**Total estimated effort:** 12-17 hours for immediate + short-term features

### Key Insights from CatPuppetBridge

**Strengths:**
- WebIRC for enhanced security and proper hostnames
- Permission-aware puppet joining (unique feature)
- Proper IRC message splitting with word boundary detection
- Exponential backoff with reasonable max delay (5 min)
- AFK/UNAFK based on Discord presence
- Queue-based architecture for command processing

**Weaknesses:**
- Threading instead of asyncio (less efficient)
- No rate limiting or flood control
- No message ID tracking for edits/deletes
- Limited error recovery

**Best practices to adopt:**
- WebIRC for all puppet connections
- Check Discord permissions before joining IRC channels
- Calculate IRC protocol overhead for accurate message splitting
- Exponential backoff with max delay cap
- Track puppet lifecycle (activate on first use, deactivate on leave)
- IRC-safe nickname generation with proper character filtering

---

## Chat-Bridge (Dolphin) Implementation Patterns

**Date:** 2026-02-19
**Source:** [chat-bridge](https://github.com/dolphin-emu/chat-bridge) - Python IRC-Discord bridge for Dolphin project

### Implementation Patterns to Adopt

1. **✅ Zero-Width Space Ping Prevention**
   - Insert `\ufeff` (zero-width space) after first character
   - Prevents accidental pings when relaying names
   - Implementation:
     ```python
     def sanitize_name(self, name):
         # Insert a zero-width space to prevent accidental pings on IRC
         return name[0] + "\ufeff" + name[1:]
     ```
   - **Priority:** High - Prevents ping spam
   - **Effort:** 15 minutes
   - **Status:** Not implemented

2. **✅ Smart IRC Nick Sanitization**
   - Full word matching algorithm (from Textual IRC client)
   - Handles `[nick]` passthrough for intentional pings
   - Word boundary detection to avoid false matches
   - Implementation:
     ```python
     def sanitize_irc_names(self, text, nicks):
         # Sort by length to match "OatmealDome" before "Oatmeal"
         sorted_nicks = sorted([n for n in nicks if n], key=len, reverse=True)
         
         # Pattern: "[nick]" (group 1) or "nick" (group 2)
         nicks_pattern = "|".join(map(re.escape, sorted_nicks))
         full_pattern = re.compile(
             f"\\[({nicks_pattern})\\]|({nicks_pattern})", re.IGNORECASE
         )
         
         def replacement_callback(match):
             # [nick] = passthrough ping
             if match.group(1):
                 return match.group(1)
             
             found_str = match.group(2)
             start, end = match.span(2)
             
             # Check word boundaries
             if found_str[0].isalnum():
                 if start > 0 and text[start - 1].isalnum():
                     return found_str  # Not a word boundary
             
             if found_str[-1].isalnum():
                 if end < len(text) and text[end].isalnum():
                     return found_str  # Not a word boundary
             
             # Match found, sanitize
             return self.sanitize_name(found_str)
         
         return full_pattern.sub(replacement_callback, text)
     ```
   - **Priority:** High - Sophisticated ping prevention
   - **Effort:** 2 hours
   - **Status:** Not implemented

3. **✅ Reply/Forward Detection**
   - Distinguish between reply and forward message types
   - Extract original sender from bot's relayed messages
   - Conditional ping based on bot mention in parent
   - Implementation:
     ```python
     def relay_discord_message(self, msg, bot_user, edited=False):
         preamble_items = []
         
         if edited:
             preamble_items.append("edited previous message")
         
         if msg.reference:
             if msg.reference.type == MessageReferenceType.reply:
                 sender = self.extract_sender_from_discord_message(
                     msg.reference.resolved, bot_user, msg
                 )
                 preamble_items.append(f"in reply to {sender}")
             elif msg.reference.type == MessageReferenceType.forward:
                 sender = self.extract_sender_from_discord_message(
                     msg.reference.resolved, bot_user
                 )
                 preamble_items.append(f"forwarded message from {sender}")
         
         preamble = "(" + ", ".join(preamble_items) + ") " if preamble_items else ""
         irc_message = f"{bold(name)}: {preamble}{text}"
     ```
   - **Priority:** Medium - Better context for replies
   - **Effort:** 1-2 hours
   - **Status:** Partial - we handle replies, not forwards

4. **✅ IRC Formatting to Discord Markdown**
   - Parse IRC color/formatting codes
   - Convert to Discord markdown equivalents
   - Escape special characters to prevent parsing
   - Implementation:
     ```python
     def format_irc_message(self, msg):
         chunklist = Tags.parse(msg)  # Parse IRC formatting
         
         ret = ""
         for chunk in chunklist.children:
             text = chunk.text
             text = text.replace("\\", "\\\\")  # Escape backslashes
             text = text.replace("<", "\\<")    # Prevent Discord parsing
             
             if "bold" in chunk.tags:
                 text = f"**{text}**"
             if "monospace" in chunk.tags:
                 text = f"`{text}`"
             if "italics" in chunk.tags:
                 text = f"*{text}*"
             if "strikethrough" in chunk.tags:
                 text = f"~~{text}~~"
             if "underline" in chunk.tags:
                 text = f"__{text}__"
             
             ret += text
         
         return ret
     ```
   - **Priority:** Medium - Better formatting preservation
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

5. **✅ Username Mention Conversion**
   - Find `[username]` patterns in IRC messages
   - Look up Discord guild members by name
   - Convert to Discord mention format `<@user_id>`
   - Implementation:
     ```python
     def relay_irc_message(self, who, what, action):
         text = f"**<{who}>** {self.format_irc_message(what)}"
         channel = self.get_channel(self.cfg.channel)
         
         def replacement_callback(match):
             username = match.group(1)
             user = channel.guild.get_member_named(username)
             
             if not user:
                 return username
             
             return f"<@{user.id}>"
         
         # Find all [username] and convert to mentions
         text = re.sub(r"\[(.*?)\]", replacement_callback, text)
         
         await channel.send(text, suppress_embeds=True)
     ```
   - **Priority:** Medium - Better mention handling
   - **Effort:** 1 hour
   - **Status:** Not implemented

6. **✅ SASL Authentication**
   - Use SASL for IRC authentication
   - More secure than NickServ IDENTIFY
   - Implementation:
     ```python
     self.ident(
         self.cfg.nick,
         sasl_username=self.cfg.sasl_username,
         sasl_password=self.cfg.sasl_password,
     )
     ```
   - **Priority:** Medium - Better security
   - **Effort:** 1 hour (if IRC library supports)
   - **Status:** Not implemented

7. **✅ Linear Reconnect Backoff**
   - Simple linear backoff: 10s, 20s, 30s, 40s...
   - Simpler than exponential, still effective
   - Implementation:
     ```python
     self.set_reconnect(lambda n: 10 * n)  # n = retry count
     ```
   - **Priority:** Medium - Alternative to exponential
   - **Effort:** 30 minutes
   - **Status:** Not implemented

8. **✅ Event Dispatcher Pattern**
   - Central event dispatcher with typed events
   - Targets register to receive specific event types
   - Graceful error handling per target
   - Implementation:
     ```python
     class Dispatcher:
         def __init__(self):
             self.targets = []
         
         def register_target(self, target):
             self.targets.append(target)
         
         def dispatch(self, source, evt):
             transmitted = {"source": source, **evt}
             for tgt in self.targets:
                 try:
                     if tgt.accept_event(transmitted):
                         tgt.push_event(transmitted)
                 except Exception:
                     logging.exception("Failed to pass event to %r", tgt)
                     continue  # Don't let one target break others
     ```
   - **Priority:** Low - We already have event bus
   - **Effort:** N/A
   - **Status:** We have similar architecture

9. **✅ Embed Suppression**
   - Use `suppress_embeds=True` when sending to Discord
   - Prevents automatic URL preview embeds
   - Implementation:
     ```python
     await channel.send(text, suppress_embeds=True)
     ```
   - **Priority:** Low - Cleaner message display
   - **Effort:** 5 minutes
   - **Status:** Not implemented

### Recommended Additions to ATL Bridge

**Immediate (High Priority):**
1. Zero-width space ping prevention - Simple and effective (15 min)
2. Smart IRC nick sanitization - Sophisticated algorithm (2 hours)

**Short-term (Medium Priority):**
3. Reply/forward detection - Better context (1-2 hours)
4. IRC formatting to Discord markdown - Better preservation (2-3 hours)
5. Username mention conversion - Better mentions (1 hour)
6. SASL authentication - Better security (1 hour)

**Long-term (Low Priority):**
7. Linear reconnect backoff - Alternative approach (30 min)
8. Embed suppression flag (5 min)

**Total estimated effort:** 8-11 hours for immediate + short-term features

### Key Insights from Chat-Bridge

**Strengths:**
- Zero-width space for ping prevention (simple, effective)
- Sophisticated word-boundary nick matching (from Textual)
- `[username]` passthrough for intentional pings
- IRC formatting to Discord markdown conversion
- Event dispatcher with graceful error handling
- SASL authentication support

**Weaknesses:**
- No puppet system (single bot)
- No message ID tracking
- No rate limiting
- Simple linear backoff (not exponential)
- Custom for Dolphin project (not general purpose)

**Best practices to adopt:**
- Zero-width space (`\ufeff`) for ping prevention
- Word boundary detection for nick matching
- Sort nicks by length to match longer names first
- `[nick]` syntax for intentional pings
- Parse IRC formatting codes and convert to Discord markdown
- `suppress_embeds=True` to prevent URL previews
- Graceful error handling in event dispatcher (don't let one target break others)

---

## Cord Implementation Patterns

**Date:** 2026-02-19
**Source:** [cord](https://git.gay/copygirl/cord) - JavaScript IRC-Discord bot framework

### Implementation Patterns to Adopt

1. **✅ Message Parts Architecture**
   - Messages composed of "parts" (strings, objects, mentions, attachments)
   - Parts can be `toString()`ed or socket-specific rendering
   - Enables rich message composition and transformation
   - Implementation:
     ```python
     @dataclass
     class MessagePart:
         pass
     
     @dataclass
     class TextPart(MessagePart):
         text: str
         def __str__(self): return self.text
     
     @dataclass
     class UserPart(MessagePart):
         user: User
         def __str__(self): return self.user.name
         def to_discord(self): return f"<@{self.user.id}>"
         def to_irc(self): return self.user.nick
     
     @dataclass
     class ActionPart(MessagePart):
         pass  # Marker for /me actions
     
     class Message:
         parts: list[MessagePart]
         
         def to_string(self) -> str:
             return "".join(str(p) for p in self.parts)
         
         def to_discord(self) -> str:
             return "".join(
                 p.to_discord() if hasattr(p, 'to_discord') else str(p)
                 for p in self.parts
             )
     ```
   - **Priority:** Medium - Better abstraction
   - **Effort:** 4-5 hours to refactor
   - **Status:** We use simple strings, not parts

2. **✅ Message Augmentation Pattern**
   - Transform message parts based on patterns (regex, class, equality)
   - Chain multiple augmentations
   - Enables flexible message processing
   - Implementation:
     ```python
     class Message:
         def augment(self, test, action):
             """Transform parts matching test using action function"""
             new_parts = []
             
             for part in self.parts:
                 # Regex test
                 if isinstance(test, re.Pattern) and isinstance(part, str):
                     match = test.search(part)
                     if match:
                         # Insert text before match
                         if match.start() > 0:
                             new_parts.append(part[:match.start()])
                         # Apply action
                         result = action(*match.groups())
                         new_parts.extend(result if isinstance(result, list) else [result])
                         # Insert text after match
                         if match.end() < len(part):
                             new_parts.append(part[match.end():])
                         continue
                 
                 # Class test
                 elif isinstance(test, type) and isinstance(part, test):
                     result = action(part)
                     new_parts.extend(result if isinstance(result, list) else [result])
                     continue
                 
                 # Equality test
                 elif part == test:
                     result = action(part)
                     new_parts.extend(result if isinstance(result, list) else [result])
                     continue
                 
                 new_parts.append(part)
             
             self.parts = new_parts
             return self  # Allow chaining
         
         def augment_clone(self, test, action):
             """Return augmented copy without modifying original"""
             cloned = Message(self.parts.copy())
             return cloned.augment(test, action)
     
     # Usage example
     message.augment(r'<@(\d+)>', lambda user_id: UserMention(user_id)) \
            .augment(ActionMarker, lambda _: ["* ", message.sender, " "]) \
            .augment(r'\n', lambda: NewLine())
     ```
   - **Priority:** Low - Interesting pattern but complex
   - **Effort:** 6-8 hours
   - **Status:** Not needed for our use case

3. **✅ Silent Message Sending**
   - `send()` triggers message events, `sendSilent()` doesn't
   - Prevents infinite loops in bridge relaying
   - Implementation:
     ```python
     class Channel:
         async def send(self, *parts, silent=False):
             message = Message(parts=parts, sender=self.bot.user, target=self)
             
             if not silent:
                 # Emit message event for other plugs/bridges
                 self.emit("message", message)
             
             # Actually send to platform
             await self._platform_send(message)
         
         async def send_silent(self, *parts):
             await self.send(*parts, silent=True)
     ```
   - **Priority:** High - Prevents bridge loops
   - **Effort:** 1 hour
   - **Status:** We check webhook_id/author, not silent flag

4. **✅ Pluggable Architecture**
   - Modular "plugs" (plugins) system
   - Common interface works across all sockets
   - Bridge plug relays between any linked channels
   - Implementation:
     ```python
     class Plug:
         def __init__(self, cord, config):
             self.cord = cord
             self.config = config
         
         def activate(self):
             """Register event handlers"""
             pass
     
     class BridgePlug(Plug):
         def activate(self):
             self.cord.on("message", self.relay_message)
         
         def relay_message(self, message):
             bridge = self.get_bridge_for_channel(message.target)
             if not bridge:
                 return
             
             # Relay to all other channels in bridge
             for channel in bridge.channels:
                 if channel != message.target:
                     channel.send_silent(*message.parts)
     ```
   - **Priority:** Low - We have adapter pattern
   - **Effort:** N/A
   - **Status:** Similar architecture already

5. **✅ IRC Flood Protection**
   - Built-in flood protection in IRC library
   - Enabled by default with `floodProtection: true`
   - Implementation:
     ```python
     # Using irc library with flood protection
     irc_options = {
         'autoConnect': False,
         'floodProtection': True,  # Built-in rate limiting
         'stripColors': True
     }
     ```
   - **Priority:** High - Already in TODO from other audits
   - **Effort:** N/A
   - **Status:** Should implement token bucket

6. **✅ Strip IRC Colors**
   - Automatically strip IRC color codes
   - Cleaner messages for Discord
   - Implementation:
     ```python
     irc_options = {
         'stripColors': True  # Remove IRC color codes
     }
     ```
   - **Priority:** Low - Simple feature
   - **Effort:** 30 minutes
   - **Status:** Not implemented

7. **✅ Resolve Strings Pattern**
   - Each resolveable (user/channel) has multiple resolve strings
   - Format: `socket_id:identifier`
   - Enables cross-platform resolution
   - Implementation:
     ```python
     class Resolveable:
         @property
         def resolve_strings(self) -> list[str]:
             """Return all strings that could resolve to this object"""
             return [
                 f"{self.socket.id}:{self.name}",
                 f"{self.socket.id}:{self.id}",
             ]
     
     class Bridge:
         def __init__(self):
             self._resolve_map = {}  # resolve_string -> bridge
         
         def register_channel(self, channel):
             for resolve in channel.resolve_strings:
                 self._resolve_map[resolve] = self.get_bridge(channel)
     ```
   - **Priority:** Low - Interesting pattern
   - **Effort:** 3-4 hours
   - **Status:** We use direct ID mapping

### Recommended Additions to ATL Bridge

**Immediate (High Priority):**
1. Silent message sending - Prevent bridge loops (1 hour)

**Short-term (Medium Priority):**
2. Message parts architecture - Better abstraction (4-5 hours)

**Long-term (Low Priority):**
3. Strip IRC colors option (30 min)
4. Message augmentation pattern (6-8 hours)
5. Resolve strings pattern (3-4 hours)

**Total estimated effort:** 15-18 hours for all features

### Key Insights from Cord

**Strengths:**
- Message parts architecture enables rich composition
- Augmentation pattern for flexible message transformation
- Silent sending prevents bridge loops
- Pluggable architecture with common interface
- Built-in IRC flood protection
- Resolve strings for cross-platform resolution

**Weaknesses:**
- JavaScript (not Python)
- Complex abstraction (parts + augmentation)
- No message ID tracking
- No retry logic
- Personal bot, not production-focused

**Best practices to adopt:**
- Silent message sending to prevent event loops
- Message parts for platform-agnostic composition
- Augmentation pattern for flexible transformations
- Built-in flood protection in IRC library
- Strip IRC colors for cleaner Discord messages
- Resolve strings for flexible object resolution

**Note:** Cord's architecture is interesting but quite different from our event-driven approach. The message parts and augmentation patterns are elegant but may be over-engineering for our use case. The most valuable takeaway is the silent sending pattern to prevent bridge loops.

---

## DevSE-Chan Implementation Patterns

**Date:** 2026-02-19
**Source:** [devse-chan](https://github.com/d0p1s4m4/devse-chan) - Python IRC-Discord bridge for DevSE

### Implementation Patterns to Adopt

1. **✅ Hash-Based Avatar Generation**
   - Generate deterministic color from nickname hash
   - Use UI Avatars API for avatar generation
   - Fallback when Discord user not found
   - Implementation:
     ```python
     def nick_to_hexcolor(nick: str) -> str:
         hash_val = 0
         for c in nick:
             hash_val = ord(c) + ((hash_val << 5) - hash_val)
         
         color = ''
         for i in range(3):
             val = (hash_val >> (i * 8)) & 0xFF
             color += ('00' + hex(val)[2:])[-2:]
         return color
     
     def gen_avatar_from_nick(nick: str) -> str:
         return f"https://eu.ui-avatars.com/api/?background={nick_to_hexcolor(nick)}&name={nick}"
     ```
   - **Priority:** Medium - Better than robohash
   - **Effort:** 30 minutes
   - **Status:** We use Portal for avatars

2. **✅ Message Edit/Delete Logging**
   - Log edits and deletes to separate channel
   - Include before/after content for edits
   - Markdown formatting for readability
   - Implementation:
     ```python
     @bot.event
     async def on_message_edit(before, after):
         if before.webhook_id:
             return
         
         data = [
             "```markdown",
             "# Message Edited",
             f"[{before.created_at}](#{before.channel})",
             f"< {before.author} >",
             "<Before  >",
             f"<Message > {before.clean_content}",
             "",
             "<After   >",
             f"<Message > {after.clean_content}",
             "```"
         ]
         
         await log_channel.send("\n".join(data))
     
     @bot.event
     async def on_message_delete(message):
         data = [
             "```markdown",
             "# Message Deleted",
             f"[{message.created_at}](#{message.channel})",
             f"< {message.author} >",
             f"<Message > {message.clean_content}",
             "```"
         ]
         
         await log_channel.send("\n".join(data))
     ```
   - **Priority:** Low - Audit feature, not core bridging
   - **Effort:** 1-2 hours
   - **Status:** Not implemented

3. **✅ Welcome/Goodbye Messages**
   - Template-based messages with substitution
   - Triggered on member join/remove
   - Includes timestamp and date
   - Implementation:
     ```python
     from string import Template
     from datetime import datetime
     
     @bot.event
     async def on_member_join(member):
         msg = Template(config['messages']['welcome'])
         now = datetime.utcnow()
         m = msg.substitute(
             name=member.display_name,
             time=now.strftime("%H:%M:%S UTC"),
             date=now.strftime("%Y-%m-%d")
         )
         await welcome_channel.send(m)
     
     @bot.event
     async def on_member_remove(member):
         msg = Template(config['messages']['goodbye'])
         now = datetime.utcnow()
         m = msg.substitute(
             name=member.display_name,
             time=now.strftime("%H:%M:%S UTC"),
             date=now.strftime("%Y-%m-%d")
         )
         await welcome_channel.send(m)
     ```
   - **Priority:** Low - Nice-to-have feature
   - **Effort:** 1 hour
   - **Status:** Not implemented

4. **✅ CTCP VERSION/SOURCE Response**
   - Respond to CTCP VERSION with system info
   - Respond to CTCP SOURCE with repository URL
   - Implementation:
     ```python
     @irc.on('privmsg')
     async def irc_message(nick, target, message, **kwargs):
         if target == config['nick']:
             if message == '\001VERSION\001':
                 system = 'GNU/Linux' if platform.system() == 'Linux' else platform.system()
                 irc.send('NOTICE', target=nick, 
                         message=f"\001VERSION devse-chan on {system}\001")
             elif message == '\001SOURCE\001':
                 irc.send('NOTICE', target=nick,
                         message='\001SOURCE https://github.com/d0p1s4m4/devse-chan\001')
     ```
   - **Priority:** Low - IRC etiquette
   - **Effort:** 30 minutes
   - **Status:** Not implemented

5. **✅ Fixed Delay Between Messages**
   - Sleep 1s before sending, 2s after sending
   - Simple flood control (not sophisticated)
   - Implementation:
     ```python
     def to_irc(self, author, msg_list):
         for msg in msg_list:
             if len(msg) > 0:
                 time.sleep(1)  # Wait before send
                 self.irc.send(author, msg)
                 time.sleep(2)  # Wait after send
     ```
   - **Priority:** Low - Too simplistic
   - **Effort:** N/A
   - **Status:** Should use token bucket instead

6. **✅ IRC Color Code in Messages**
   - Use `\x03` color codes for nicknames
   - Color 6 (magenta) for bridged nicknames
   - Implementation:
     ```python
     def send(self, nick, message):
         # \x036 = magenta color, \x0F = reset
         self.irc.send('PRIVMSG', target=channel, 
                      message=f"<\x036{nick}\x0F> {message}")
     ```
   - **Priority:** Low - Cosmetic feature
   - **Effort:** 15 minutes
   - **Status:** Not implemented

7. **✅ Confuse Configuration Library**
   - YAML-based configuration with validation
   - Hierarchical config access
   - Implementation:
     ```python
     import confuse
     
     config = confuse.Configuration('devsechan')
     # Access: config['discord']['token'].get()
     ```
   - **Priority:** Low - We use pydantic
   - **Effort:** N/A
   - **Status:** We have better config system

### Recommended Additions to ATL Bridge

**Immediate (High Priority):**
- None (no critical patterns)

**Short-term (Medium Priority):**
1. Hash-based avatar generation - Better fallback (30 min)

**Long-term (Low Priority):**
2. Message edit/delete logging - Audit feature (1-2 hours)
3. Welcome/goodbye messages - Community feature (1 hour)
4. CTCP VERSION/SOURCE - IRC etiquette (30 min)
5. IRC color codes for nicknames - Cosmetic (15 min)

**Total estimated effort:** 3-4 hours for all features

### Key Insights from DevSE-Chan

**Strengths:**
- Simple, focused implementation (~200 LOC)
- Hash-based avatar generation (deterministic colors)
- Message edit/delete logging for moderation
- Template-based welcome/goodbye messages
- CTCP VERSION/SOURCE responses

**Weaknesses:**
- Fixed delays instead of proper rate limiting (1s + 2s)
- No message ID tracking
- No retry logic
- No error recovery
- Very basic implementation

**Best practices to adopt:**
- Hash-based avatar color generation (deterministic)
- UI Avatars API for fallback avatars
- Message edit/delete logging to separate channel
- Template-based messages with datetime substitution
- CTCP VERSION/SOURCE responses for IRC etiquette

**Note:** DevSE-Chan is a very simple bridge (~200 lines) with basic features. The most useful pattern is the hash-based avatar generation which provides consistent, deterministic colors for IRC users. The fixed delay approach (sleep 1s + 2s) is too simplistic and should be replaced with proper token bucket rate limiting. Most other features are nice-to-have but not critical for core bridging functionality.

---

## Unifier Implementation Patterns

**Date:** 2026-02-19
**Source:** [unifier](https://github.com/UnifierHQ/unifier) - Python Discord bridge with external platform support

### Implementation Patterns to Adopt

1. **✅ Performance Optimizations**
   - Optional ujson for faster JSON parsing
   - Optional uvloop for faster asyncio event loop
   - aiomultiprocess for parallel message sending
   - Implementation:
     ```python
     # Import ujson if available for 2-3x faster JSON
     try:
         import ujson as json
     except ImportError:
         import json
     
     # Import uvloop if available for faster event loop
     try:
         import uvloop
         uvloop.install()
     except ImportError:
         pass
     
     # Use aiomultiprocess for parallel operations
     import aiomultiprocess
     from aiomultiprocess import Worker
     
     if not sys.platform == 'win32':
         aiomultiprocess.set_start_method("fork")
     ```
   - **Priority:** Medium - Performance boost
   - **Effort:** 30 minutes
   - **Status:** Not implemented

2. **✅ Webhook Cache Store**
   - In-memory webhook cache per server
   - Avoid repeated webhook fetches
   - Store by identifier for quick lookup
   - Implementation:
     ```python
     class WebhookCacheStore:
         def __init__(self, bot):
             self.bot = bot
             self.webhooks = {}  # {server_id: {identifier: webhook}}
         
         def store_webhook(self, webhook, identifier, server):
             self.webhooks.setdefault(server, {})[identifier] = webhook
             return len(self.webhooks[server])
         
         def get_webhook(self, identifier):
             for guild in self.webhooks.keys():
                 if identifier in self.webhooks[guild]:
                     return self.webhooks[guild][identifier]
             raise ValueError('invalid webhook')
         
         def get_webhooks(self, server):
             if not self.webhooks[server]:
                 raise ValueError('no webhooks')
             return list(self.webhooks[server].values())
         
         def clear(self, server=None):
             if server:
                 self.webhooks[server] = {}
             else:
                 self.webhooks = {}
     ```
   - **Priority:** High - Reduces API calls
   - **Effort:** 1 hour
   - **Status:** Partial - we cache but not as structured

3. **✅ Message Cache Backup**
   - Backup message cache on graceful shutdown
   - Persist message IDs between restarts
   - Enables reply/edit/delete after restart
   - Implementation:
     ```python
     import compress_json
     
     async def backup_message_cache(self):
         self.logger.info("Backing up message cache...")
         cache_data = {
             'messages': self.message_cache,
             'timestamp': time.time()
         }
         compress_json.dump(cache_data, 'message_cache.json.gz')
     
     async def load_message_cache(self):
         try:
             cache_data = compress_json.load('message_cache.json.gz')
             self.message_cache = cache_data['messages']
             self.logger.info(f"Loaded {len(self.message_cache)} cached messages")
         except FileNotFoundError:
             self.message_cache = {}
     ```
   - **Priority:** High - Better reliability
   - **Effort:** 2 hours
   - **Status:** Not implemented

4. **✅ Deduplication Emojis**
   - Visual indicators for message deduplication
   - Colored square emojis to identify duplicates
   - Implementation:
     ```python
     dedupe_emojis = [
         '\U0001F7E5',  # Red square
         '\U0001F7E7',  # Orange square
         '\U0001F7E8',  # Yellow square
         '\U0001F7E9',  # Green square
         '\U0001F7E6',  # Blue square
         '\U0001F7EA',  # Purple square
         '\U0001F7EB',  # Brown square
         '\U00002B1C',  # White square
         '\U00002B1B'   # Black square
     ]
     
     def get_dedupe_emoji(message_id):
         # Use message ID to deterministically pick emoji
         return dedupe_emojis[hash(message_id) % len(dedupe_emojis)]
     ```
   - **Priority:** Low - Visual feature
   - **Effort:** 30 minutes
   - **Status:** Not implemented

5. **✅ AllowedMentions Configuration**
   - Disable @everyone and role mentions by default
   - Emergency mentions for alerts
   - Implementation:
     ```python
     mentions = nextcord.AllowedMentions(
         everyone=False,
         roles=False,
         users=False
     )
     
     emergency_mentions = nextcord.AllowedMentions(
         everyone=False,
         roles=True,
         users=True
     )
     
     # Use in messages
     await channel.send(content, allowed_mentions=mentions)
     ```
   - **Priority:** High - Security/anti-abuse
   - **Effort:** 15 minutes
   - **Status:** Not implemented

6. **✅ Plugin System**
   - External platform support via plugins
   - Revolt and Guilded support plugins
   - Extensible architecture
   - Implementation:
     ```python
     class PlatformPlugin:
         def __init__(self, bot):
             self.bot = bot
         
         async def send_message(self, channel_id, content):
             raise NotImplementedError
         
         async def on_message(self, message):
             raise NotImplementedError
     
     # Load plugins
     plugins = {}
     for plugin_file in os.listdir('plugins'):
         if plugin_file.endswith('.py'):
             module = importlib.import_module(f'plugins.{plugin_file[:-3]}')
             plugins[module.PLATFORM_NAME] = module.Plugin(bot)
     ```
   - **Priority:** Low - We focus on IRC/XMPP/Discord
   - **Effort:** N/A
   - **Status:** Not needed for our scope

7. **✅ Built-in Upgrader**
   - Automatic config migration
   - Version management
   - Easy updates
   - Implementation:
     ```python
     async def upgrade(self):
         current_version = self.config['version']
         latest_version = await self.fetch_latest_version()
         
         if current_version < latest_version:
             await self.backup_config()
             await self.download_update()
             await self.migrate_config(current_version, latest_version)
             await self.restart()
     ```
   - **Priority:** Low - Nice-to-have
   - **Effort:** 4-5 hours
   - **Status:** Not implemented

8. **✅ Compressed JSON Storage**
   - Use compress_json for data storage
   - Reduces disk usage
   - Implementation:
     ```python
     import compress_json
     
     # Save
     compress_json.dump(data, 'data.json.gz')
     
     # Load
     data = compress_json.load('data.json.gz')
     ```
   - **Priority:** Low - Optimization
   - **Effort:** 30 minutes
   - **Status:** Not implemented

### Recommended Additions to ATL Bridge

**Immediate (High Priority):**
1. Webhook cache store - Reduce API calls (1 hour)
2. Message cache backup - Persist between restarts (2 hours)
3. AllowedMentions configuration - Security (15 min)

**Short-term (Medium Priority):**
4. Performance optimizations - ujson + uvloop (30 min)

**Long-term (Low Priority):**
5. Deduplication emojis - Visual indicators (30 min)
6. Compressed JSON storage - Disk optimization (30 min)
7. Built-in upgrader - Easy updates (4-5 hours)

**Total estimated effort:** 8-10 hours for immediate + short-term features

### Key Insights from Unifier

**Strengths:**
- Production-focused with 33 msg/s throughput claim
- Performance optimizations (ujson, uvloop, aiomultiprocess)
- Webhook caching reduces API calls
- Message cache backup for persistence
- AllowedMentions for security
- Plugin system for extensibility
- Built-in upgrader for easy maintenance
- Compressed JSON for storage efficiency

**Weaknesses:**
- Large codebase (complex)
- Discord-focused (limited IRC/XMPP)
- AGPLv3 license (copyleft)

**Best practices to adopt:**
- Optional performance libraries (ujson, uvloop)
- Structured webhook cache with per-server storage
- Message cache backup on graceful shutdown
- AllowedMentions to prevent mention abuse
- Compressed JSON for efficient storage
- Deduplication emojis for visual feedback

**Note:** Unifier is a large, production-focused Discord bridge with impressive performance claims (33 msg/s). The most valuable patterns are the webhook cache store, message cache backup, and performance optimizations. The plugin system is interesting but out of scope for our IRC/XMPP/Discord focus. The AllowedMentions configuration is a simple but important security feature we should adopt.

### 9. **✅ Link Buttons for Replies**
   - Use Discord link buttons to show reply context
   - Jump to original message with URL button
   - Compact and comfortable display modes
   - Implementation:
     ```python
     import nextcord
     
     # Compact mode - single button with reply arrow emoji
     components = nextcord.ui.View()
     components.add_item(
         nextcord.ui.Button(
             style=nextcord.ButtonStyle.url,
             label="↩️ Reply to @username",
             emoji='↩️',
             url=message_url,
             disabled=message_url is None
         )
     )
     
     # Comfortable mode - two buttons (heading + content preview)
     components.add_item(
         nextcord.ui.Button(
             style=nextcord.ButtonStyle.url,
             label="Replying to @username",
             url=message_url
         )
     )
     
     # Second button with content preview
     components.add_item(
         nextcord.ui.Button(
             style=nextcord.ButtonStyle.blurple,  # Color by platform
             label="Message content preview...",
             emoji='🏞️' if has_attachments else None,
             url=message_url
         )
     )
     
     await channel.send(content, view=components)
     ```
   - **Priority:** Medium - Better UX for replies
   - **Effort:** 2-3 hours
   - **Status:** Not implemented
   - **Benefits:**
     - Visual reply context without quoting full message
     - Jump to original message with one click
     - Cleaner than text-based reply indicators
     - Platform-specific button colors (Discord=blue, Revolt=red, etc.)
     - Attachment indicator emoji

**Updated total estimated effort:** 10-13 hours for immediate + short-term features

---

## DIBridge (OpenTTD) Implementation Patterns

**Date:** 2026-02-19
**Source:** [dibridge](https://github.com/OpenTTD/dibridge) - Python Discord-IRC bridge by OpenTTD

### Implementation Patterns to Adopt

1. **✅ IPv6 CIDR Range for IRC Puppets**
   - Assign unique IPv6 address to each Discord user's IRC puppet
   - Bypasses IRC network connection limits (typically 3 per IP)
   - Deterministic IP assignment (same user = same IP)
   - Implementation:
     ```python
     import ipaddress
     import hashlib
     
     class IRCPuppetManager:
         def __init__(self, puppet_ip_range: str):
             # e.g., "2001:db8::/80"
             self.puppet_ip_range = ipaddress.ip_network(puppet_ip_range)
             
             if self.puppet_ip_range.num_addresses < 2**32:
                 raise ValueError("IPv6 CIDR range must be at least /96")
         
         def generate_ipv6_for_user(self, discord_username: str):
             # Hash username to get deterministic IP
             hash_val = int(
                 hashlib.sha256(discord_username.encode()).hexdigest(),
                 16
             )
             offset = hash_val % self.puppet_ip_range.num_addresses
             return self.puppet_ip_range[offset]
         
         async def connect_puppet(self, username: str):
             ipv6_address = self.generate_ipv6_for_user(username)
             local_addr = (str(ipv6_address), 0)
             
             # Connect with specific source IP
             await connection.connect(
                 irc_host,
                 irc_port,
                 nickname,
                 connect_factory=irc.connection.AioFactory(
                     family=socket.AF_INET6,
                     local_addr=local_addr,
                     ssl=use_ssl
                 )
             )
     ```
   - **Priority:** Low - Advanced feature, requires infrastructure
   - **Effort:** 4-5 hours + infrastructure setup
   - **Status:** Not implemented
   - **Requirements:**
     - Linux 4.3+ kernel
     - IPv6 prefix delegation (at least /96, preferably /80)
     - Kernel config: `sysctl -w net.ipv6.ip_nonlocal_bind=1`
     - Route setup: `ip route add local 2001:db8::/80 dev eth0`
   - **Benefits:**
     - Native IRC feel (each Discord user = separate IRC connection)
     - Tab completion works (`us<tab>` → `username`)
     - IRC bans work per-user (same user always gets same IP)
     - Bypasses connection limits on IRC networks
     - No `<username> message` prefix needed

2. **✅ Nickname Collision Handling**
   - Try `[d]` suffix first (Discord indicator)
   - Fall back to `[1]`, `[2]`, etc.
   - Automatic nick reclaim after netsplit
   - Implementation:
     ```python
     def on_nicknameinuse(self, client, event):
         # First try: add [d] for Discord
         if self.nickname_iteration == 0:
             self.nickname = f"{self.nickname_original}[d]"
             self.nickname_iteration += 1
             client.nick(self.nickname)
             return
         
         # Subsequent tries: add [1], [2], etc.
         self.nickname = f"{self.nickname_original}[{self.nickname_iteration}]"
         self.nickname_iteration += 1
         client.nick(self.nickname)
     
     def on_nick(self, client, event):
         if event.source.nick == self.nickname:
             # Server changed our nick (netsplit, GHOST, etc.)
             self.log.info("Nick changed to '%s' by server; reclaiming", event.target)
             asyncio.create_task(self.reclaim_nick())
     
     async def reclaim_nick(self):
         # Wait 1 second to avoid racing with legitimate users
         await asyncio.sleep(1)
         self.nickname = self.nickname_original
         self.nickname_iteration = 0
         self.client.nick(self.nickname)
     ```
   - **Priority:** Medium - Better nick handling
   - **Effort:** 1 hour
   - **Status:** Partial - we handle collisions but not reclaim

3. **✅ Puppet Idle Timeout**
   - Disconnect puppets after inactivity (default: 2 days)
   - Configurable timeout per puppet
   - Automatic cleanup
   - Implementation:
     ```python
     async def start_idle_timeout(self):
         await self.stop_idle_timeout()
         self.idle_task = asyncio.create_task(self._idle_timeout_task())
     
     async def stop_idle_timeout(self):
         if self.idle_task:
             self.idle_task.cancel()
             self.idle_task = None
     
     async def _idle_timeout_task(self):
         await asyncio.sleep(self.idle_timeout)  # e.g., 2 days
         
         self.reconnect = False
         self.client.disconnect("User went offline on Discord a while ago")
         await self.remove_puppet_func()
     
     # Reset timeout on activity
     async def on_message_sent(self):
         await self.start_idle_timeout()  # Reset timer
     ```
   - **Priority:** High - Already in TODO
   - **Effort:** 1 hour
   - **Status:** We have 24h timeout, should make configurable

4. **✅ Random IPv6 Host Selection**
   - IRC servers often have multiple IPv6 addresses
   - Pick random one to distribute load
   - Avoid RFC getaddrinfo() sorting bias
   - Implementation:
     ```python
     import random
     import socket
     
     async def connect_to_irc(self, irc_host: str):
         # Get all IPv6 addresses for host
         ipv6s = await self.loop.getaddrinfo(
             irc_host,
             None,
             family=socket.AF_INET6,
             type=socket.SOCK_STREAM,
             proto=socket.IPPROTO_TCP
         )
         
         if not ipv6s:
             raise ConnectionError("No IPv6 addresses found")
         
         # Pick random one to distribute load
         irc_host_ipv6 = random.choice(ipv6s)[4][0]
         
         self.log.info("Connecting to %s (%s)", irc_host, irc_host_ipv6)
         await self.connection.connect(irc_host_ipv6, port, nick)
     ```
   - **Priority:** Low - Optimization
   - **Effort:** 30 minutes
   - **Status:** Not implemented

5. **✅ Puppet Pinger Task**
   - Send PING every 120 seconds to keep connection alive
   - Prevent idle disconnects
   - Implementation:
     ```python
     async def _pinger(self):
         while True:
             await asyncio.sleep(120)
             self.client.ping("keep-alive")
     
     def on_welcome(self, client, event):
         if self.pinger_task:
             self.pinger_task.cancel()
         self.pinger_task = asyncio.create_task(self._pinger())
     ```
   - **Priority:** Medium - Keep-alive
   - **Effort:** 30 minutes
   - **Status:** Not implemented

### Recommended Additions to ATL Bridge

**Immediate (High Priority):**
- None (IPv6 puppets require infrastructure)

**Short-term (Medium Priority):**
1. Nickname collision handling with reclaim (1 hour)
2. Puppet pinger task - Keep-alive (30 min)

**Long-term (Low Priority):**
3. IPv6 CIDR range for puppets - Advanced feature (4-5 hours + infra)
4. Random IPv6 host selection - Load distribution (30 min)

**Total estimated effort:** 2-6.5 hours (excluding IPv6 infrastructure)

### Key Insights from DIBridge

**Strengths:**
- IPv6 CIDR range for puppets is innovative and elegant
- Solves IRC connection limit problem
- Native IRC feel (no `<username>` prefix)
- Deterministic IP assignment (same user = same IP)
- Nickname collision handling with reclaim
- Puppet idle timeout for cleanup

**Weaknesses:**
- Requires IPv6 infrastructure and kernel config
- Linux 4.3+ only for IPv6 binding
- Single channel bridge only
- No edit/reaction support

**Best practices to adopt:**
- IPv6 puppet addressing (if infrastructure available)
- Nickname collision handling with `[d]` suffix
- Automatic nick reclaim after netsplit
- Puppet idle timeout (configurable)
- Pinger task for keep-alive
- Random IPv6 host selection for load distribution

**Note:** DIBridge's IPv6 CIDR range for puppets is a brilliant solution to IRC connection limits, but requires significant infrastructure setup (IPv6 prefix delegation, kernel config, routing). The nickname collision handling and puppet idle timeout are more immediately applicable patterns. The approach gives a truly native IRC feel where each Discord user appears as a separate IRC user with their own connection and IP address.

---

## Dis4IRC Implementation Patterns

**Date:** 2026-02-19
**Source:** [Dis4IRC](https://github.com/zachbr/Dis4IRC) - Kotlin Discord-IRC bridge

### Implementation Patterns to Adopt

1. **✅ Mutator Pattern for Message Processing**
   - Plugin-like system for message transformations
   - Each mutator can modify message or halt processing
   - Lifecycle control (CONTINUE, STOP, DISCARD)
   - Track applied mutators to prevent double-application
   - Implementation:
     ```python
     from enum import Enum
     from typing import Protocol
     
     class LifeCycle(Enum):
         CONTINUE = "continue"  # Continue to next mutator
         STOP = "stop"          # Stop processing, send message
         DISCARD = "discard"    # Discard message entirely
     
     class Mutator(Protocol):
         def mutate(self, message: Message) -> LifeCycle:
             ...
     
     class MutatorManager:
         def __init__(self):
             self.mutators: list[Mutator] = []
         
         def register_mutator(self, mutator: Mutator):
             self.mutators.append(mutator)
         
         def apply_mutators(self, message: Message) -> Message | None:
             for mutator in self.mutators:
                 # Skip if already applied
                 if mutator.__class__ in message.applied_mutators:
                     continue
                 
                 lifecycle = mutator.mutate(message)
                 message.applied_mutators.add(mutator.__class__)
                 
                 if lifecycle == LifeCycle.DISCARD:
                     return None
                 elif lifecycle == LifeCycle.STOP:
                     break
             
             return message
     ```
   - **Priority:** Medium - Clean architecture
   - **Effort:** 3-4 hours
   - **Status:** Not implemented

2. **✅ Automatic Paste Service for Long Messages**
   - Upload long messages to paste service
   - Replace with short summary + paste URL
   - Configurable thresholds (length, newlines, code blocks)
   - Implementation:
     ```python
     class PasteLongMessages(Mutator):
         def __init__(self, config):
             self.max_newlines = config.get('max_new_lines', 4)
             self.max_length = config.get('max_message_length', 450)
             self.paste_expiry_days = config.get('paste_expiration_in_days', 7)
         
         def mutate(self, message: Message) -> LifeCycle:
             # Only paste Discord messages going to IRC
             if message.source != 'discord':
                 return LifeCycle.CONTINUE
             
             should_paste = False
             
             # Check newline count
             if message.content.count('\n') > self.max_newlines:
                 should_paste = True
             
             # Check for code blocks
             if message.content.count('```') >= 2:
                 should_paste = True
             
             # Check length
             if len(message.content) > self.max_length:
                 should_paste = True
             
             if not should_paste:
                 return LifeCycle.CONTINUE
             
             # Upload to paste service
             paste_url = await self.upload_paste(message.content)
             
             # Replace message with summary
             preview = message.content[:100] + "..." if len(message.content) > 100 else message.content
             message.content = f"{preview}\nFull message: {paste_url}"
             
             return LifeCycle.CONTINUE
     ```
   - **Priority:** High - Better UX for long messages
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

3. **✅ Strategic Zero-Width Space Insertion**
   - Insert `\u200B` (zero-width space) in nicknames
   - Prevents accidental pings
   - Place after vowels for natural breaking
   - Implementation:
     ```python
     ANTI_PING_CHAR = '\u200B'  # Zero-width space
     
     def rebuild_with_anti_ping(nick: str) -> str:
         """Insert zero-width space after vowels to prevent pings"""
         vowels = set('aeiouAEIOU')
         result = []
         
         for i, char in enumerate(nick):
             result.append(char)
             # Insert after vowels (but not at end)
             if char in vowels and i < len(nick) - 1:
                 result.append(ANTI_PING_CHAR)
         
         return ''.join(result)
     
     # Usage
     safe_nick = rebuild_with_anti_ping("username")  # "us\u200Bern\u200Bame"
     ```
   - **Priority:** High - Already in TODO from other audits
   - **Effort:** 30 minutes
   - **Status:** Not implemented

4. **✅ Strip Anti-Ping Characters Mutator**
   - Remove zero-width spaces from IRC → Discord
   - Clean up for Discord display
   - Implementation:
     ```python
     class StripAntiPingCharacters(Mutator):
         def mutate(self, message: Message) -> LifeCycle:
             if message.source == 'irc':
                 message.content = message.content.replace('\u200B', '')
             return LifeCycle.CONTINUE
     ```
   - **Priority:** Medium - Cleanup
   - **Effort:** 15 minutes
   - **Status:** Not implemented

5. **✅ No-Prefix Regex for Bot Commands**
   - Allow IRC bot commands without username prefix
   - Configurable regex pattern
   - Example: `^\\.[A-Za-z0-9]` matches `.help`, `.info`
   - Implementation:
     ```python
     import re
     
     class BotCommandHandler:
         def __init__(self, no_prefix_pattern: str):
             self.no_prefix_regex = re.compile(no_prefix_pattern)
         
         def should_add_prefix(self, message: str) -> bool:
             """Check if message should have sender prefix"""
             return not self.no_prefix_regex.match(message)
         
         def format_message(self, sender: str, content: str) -> str:
             if self.should_add_prefix(content):
                 return f"<{sender}> {content}"
             else:
                 return content  # Send as-is for bot commands
     
     # Config: no-prefix-regex: "^\\.[A-Za-z0-9]"
     # ".help" → ".help" (no prefix)
     # "hello" → "<username> hello" (with prefix)
     ```
   - **Priority:** Medium - Better bot integration
   - **Effort:** 1 hour
   - **Status:** Not implemented

6. **✅ Nickname Color Support**
   - Use IRC color codes for nicknames
   - Configurable enable/disable
   - Implementation:
     ```python
     def create_sender_prefix(sender: str, use_color: bool, anti_ping: bool) -> str:
         name = sender
         
         if anti_ping:
             name = rebuild_with_anti_ping(name)
         
         if use_color:
             # Hash username to get consistent color
             color_code = hash(sender) % 16
             name = f"\x03{color_code:02d}{name}\x03"
         
         return f"<{name}>"
     ```
   - **Priority:** Low - Cosmetic
   - **Effort:** 30 minutes
   - **Status:** Not implemented

7. **✅ Statistics Manager**
   - Track messages bridged per direction
   - Uptime tracking
   - Expose via command
   - Implementation:
     ```python
     class StatisticsManager:
         def __init__(self):
             self.start_time = time.time()
             self.messages_discord_to_irc = 0
             self.messages_irc_to_discord = 0
         
         def record_message(self, source: str):
             if source == 'discord':
                 self.messages_discord_to_irc += 1
             else:
                 self.messages_irc_to_discord += 1
         
         def get_stats(self) -> dict:
             uptime = time.time() - self.start_time
             return {
                 'uptime_seconds': uptime,
                 'discord_to_irc': self.messages_discord_to_irc,
                 'irc_to_discord': self.messages_irc_to_discord,
                 'total': self.messages_discord_to_irc + self.messages_irc_to_discord
             }
     ```
   - **Priority:** Low - Monitoring
   - **Effort:** 1 hour
   - **Status:** Not implemented

### Recommended Additions to ATL Bridge

**Immediate (High Priority):**
1. Automatic paste service for long messages (2-3 hours)
2. Strategic zero-width space insertion (30 min)

**Short-term (Medium Priority):**
3. Mutator pattern for message processing (3-4 hours)
4. Strip anti-ping characters (15 min)
5. No-prefix regex for bot commands (1 hour)

**Long-term (Low Priority):**
6. Nickname color support (30 min)
7. Statistics manager (1 hour)

**Total estimated effort:** 8-10 hours for immediate + short-term features

### Key Insights from Dis4IRC

**Strengths:**
- Mutator pattern provides clean, extensible architecture
- Automatic paste service for long messages (smart thresholds)
- Strategic zero-width space placement (after vowels)
- No-prefix regex for bot command passthrough
- Lifecycle control for message processing
- Statistics tracking

**Weaknesses:**
- Kotlin (not Python, harder to adapt)
- No multi-presence/puppets
- Single channel bridge

**Best practices to adopt:**
- Mutator pattern for extensible message processing
- Automatic paste service with configurable thresholds
- Zero-width space after vowels (more natural than after first char)
- Strip anti-ping chars when going back to Discord
- No-prefix regex for bot commands
- Track applied mutators to prevent double-application
- Lifecycle control (CONTINUE, STOP, DISCARD)

**Note:** Dis4IRC's mutator pattern is elegant and provides a clean way to add message transformations. The automatic paste service is particularly useful for handling long messages and code blocks. The strategic placement of zero-width spaces after vowels is more sophisticated than simple insertion after the first character. The no-prefix regex allows IRC bot commands to work naturally without username prefixes.

---

## discord-irc (Reactiflux) Implementation Patterns

**Date:** 2026-02-19
**Source:** [discord-irc](https://github.com/reactiflux/discord-irc) - JavaScript Discord-IRC bridge by Reactiflux

### Implementation Patterns to Adopt

1. **✅ IRC Formatting Library**
   - Use `irc-formatting` library for bidirectional conversion
   - Discord markdown ↔ IRC control codes
   - Already handles: bold, italic, underline, strikethrough
   - **Priority:** Medium - Already in TODO from other audits
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

2. **✅ Auto-Send Commands on Connect**
   - Execute IRC commands automatically after connection
   - Useful for NickServ IDENTIFY, MODE changes, etc.
   - Config: `autoSendCommands: [["PRIVMSG", "NickServ", "IDENTIFY password"]]`
   - **Priority:** Medium - Convenience feature
   - **Effort:** 1 hour
   - **Status:** Not implemented

3. **✅ Custom Format Strings**
   - Template-based message formatting
   - Patterns: `{$nickname}`, `{$text}`, `{$attachmentURL}`
   - Config: `format: { ircText: "<{$displayUsername}> {$text}" }`
   - **Priority:** Low - Customization
   - **Effort:** 1-2 hours
   - **Status:** Not implemented

4. **✅ Webhook Avatar URL Template**
   - Custom avatar URL for unknown IRC users
   - Default: `https://robohash.org/{$nickname}`
   - Config: `format: { webhookAvatarURL: "https://robohash.org/{$nickname}" }`
   - **Priority:** Low - Already in TODO (robohash)
   - **Effort:** 30 minutes
   - **Status:** Not implemented

**Total estimated effort:** 4.5-6.5 hours

### Key Insights from discord-irc

**Strengths:**
- Popular, well-maintained (Reactiflux)
- IRC formatting library for bidirectional conversion
- Auto-send commands on connect
- Custom format strings for flexibility
- Webhook support with avatar templates

**Weaknesses:**
- No puppets (single bot)
- JavaScript (not Python)
- Basic feature set

**Best practices to adopt:**
- Use dedicated IRC formatting library
- Auto-send commands for NickServ/MODE
- Template-based message formatting
- Robohash for avatar generation

**Note:** discord-irc is a mature, popular bridge used by Reactiflux. Most of its patterns have been covered by other audits. The main takeaway is using a dedicated IRC formatting library for bidirectional markdown ↔ IRC control code conversion, and the auto-send commands feature for post-connection setup.

---

## Discord-IRC-Python Audit (Python) - 2026-02-19

**Repository**: Simple Discord-IRC bridge using threading  
**Language**: Python 3.5+  
**Architecture**: Threading-based with shared lock  
**Assessment**: Basic implementation with minimal features

### Patterns Identified

1. **✅ Markdown Escaping for IRC Nicks**
   - IRC → Discord: Escapes markdown special chars in nicknames
   - Prevents IRC nicks from breaking Discord formatting
   - Pattern: `re.sub(r"(]|-|\\|[`*_{}[()#+.!])", r'\\\1', nick)`
   - Escapes: `] - \ [ ` * _ { } [ ( ) # + . !`
   - **Priority:** Medium - Prevents formatting issues
   - **Effort:** 1-2 hours
   - **Status:** Not implemented

2. **Threading Architecture** (Not Applicable)
   - Separate threads for IRC and Discord clients
   - Shared `threading.Lock()` for console output synchronization
   - Daemon thread for IRC (dies when main thread exits)
   - **Assessment:** Our async architecture is superior; no action needed

3. **Attachment Handling** (Already Better)
   - Appends first attachment URL to message content
   - Pattern: `content += ' ' + message.attachments[0].url`
   - Only handles first attachment, ignores rest
   - **Assessment:** We already handle attachments better; no action needed

4. **Bot Owner Commands** (Low Priority)
   - `!quit` command restricted to bot owner
   - Checks `message.author.name == settings["botowner"]`
   - **Priority:** Low - Admin commands consideration
   - **Effort:** 1 hour
   - **Status:** Not implemented

5. **Clean Content Usage** (Already Implemented)
   - Uses `message.clean_content` for Discord messages
   - Converts mentions to readable format automatically
   - **Assessment:** ✅ We already use this pattern

6. **Nickname Collision Handling** (Low Priority)
   - Appends `_` to nickname on collision
   - Pattern: `connection.nick(connection.get_nickname() + "_")`
   - **Assessment:** Basic approach; we may need better collision handling for puppets
   - **Priority:** Low - Already covered in other audits
   - **Effort:** 30 minutes
   - **Status:** Not implemented

### Patterns NOT Worth Implementing
- Threading model (we use async)
- Global variables (poor design)
- Latin-1 encoding (we use UTF-8)
- Synchronous message sending (we use async)
- Single attachment handling (we handle multiple)
- Recursive reconnection (we have better retry logic)

### Key Insights from Discord-IRC-Python

**Strengths:**
- Simple, minimal implementation
- Markdown escaping for IRC nicks
- Clean content usage

**Weaknesses:**
- Threading instead of async
- Global variables
- No puppets (single bot)
- Basic feature set
- Poor error handling
- No flood control
- Latin-1 encoding

**Best practices to adopt:**
- Markdown escaping for IRC nicks in Discord messages

**Total estimated effort:** 1-2 hours (markdown escaping only)

**Priority Assessment:**
- **Immediate:** None
- **Short-term:** Markdown escaping for IRC nicks (1-2 hours)
- **Long-term:** Bot owner commands consideration

---

## discord-irc-rs Audit (Rust) - 2026-02-19

**Repository**: Discord-IRC bridge written in Rust  
**Language**: Rust (2024 edition)  
**Architecture**: Async with tokio, serenity (Discord), libirc (IRC)  
**Assessment**: Well-structured Rust implementation with unique features

### Patterns Identified

1. **✅ Strategic Zero-Width Space Insertion**
   - Inserts zero-width spaces (U+200B) into nicknames to prevent mentions
   - Uses Unicode grapheme segmentation for proper character handling
   - Inserts at 1/3 and 2/3 positions for nicknames with 3+ graphemes
   - Pattern: `insert_zero_width_spaces_into_nickname()`
   - **Priority:** High - Better than simple insertion after first char
   - **Effort:** 2-3 hours (requires unicode-segmentation library)
   - **Status:** Not implemented

2. **✅ IRC Nickname Normalization**
   - Replaces special chars that conflict with IRC/Discord
   - `!` → `ǃ` (U+0021 → U+01C3) - Prevents hostmask confusion
   - `@` → `＠` (U+0040 → U+FE6B) - Prevents mention conflicts
   - Space → `_` - IRC compatibility
   - **Priority:** Medium - Prevents protocol conflicts
   - **Effort:** 1 hour
   - **Status:** Not implemented

3. **✅ Auto-Detect Avatar from Discord**
   - Searches Discord channel members for matching nickname
   - Uses Discord cache to find user with same display name
   - Automatically sets webhook avatar to user's Discord avatar
   - Requires GUILD_MEMBERS and GUILD_PRESENCES intents
   - **Priority:** Medium - Better UX than robohash
   - **Effort:** 3-4 hours
   - **Status:** Not implemented

4. **✅ IRC Formatting to Discord Markdown Conversion**
   - Comprehensive IRC control code parser with state machine
   - Handles: Bold (0x02), Italic (0x1d), Underline (0x1f), Strikethrough (0x1e), Monospace (0x11)
   - Color codes (0x03) with fg/bg support → Discord spoilers when fg==bg
   - Reverse color (0x16), Reset (0x0f)
   - Escapes Discord markdown in non-URL text: `_ * ` > \`
   - URL detection with regex, preserves underscores in URLs
   - Stack-based formatting state management
   - **Priority:** High - Professional IRC formatting support
   - **Effort:** 8-12 hours (complex state machine)
   - **Status:** Not implemented

5. **✅ Ozinger Network Support (FAKEMSG)**
   - Special support for ozinger.org IRC network
   - Uses `FAKEMSG` command for puppet-like behavior without actual puppets
   - Format: `FAKEMSG nick＠d!{hex_id}@pbzweihander/discord-irc-rs #channel message`
   - Sends OPER command on connect for authentication
   - **Priority:** Low - Network-specific feature
   - **Effort:** N/A (not applicable to our use case)
   - **Status:** Not applicable

6. **✅ Bridge Member Changes (JOIN/PART/KICK)**
   - Configurable bridging of IRC member events to Discord
   - JOIN: "**nickname** has joined the channel."
   - PART/QUIT: "**nickname** has left the channel. (`reason`)"
   - KICK: "**nickname** has been kicked by **kicker**. (`reason`)"
   - Config: `bridge_member_changes = true/false`
   - **Priority:** Medium - Already in our TODO
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

7. **✅ Exit on Send Error**
   - Configurable behavior: exit or continue on send errors
   - Uses `stopper` pattern for graceful shutdown
   - Config: `exit_on_send_error = true/false`
   - **Priority:** Low - Error handling policy
   - **Effort:** 1 hour
   - **Status:** Not implemented

8. **✅ Multi-line Message Handling**
   - Splits Discord messages by newlines
   - Sends each line as separate IRC message
   - Appends attachment URLs as additional lines
   - Pattern: `content.split('\n').chain(attachments.map(|at| at.url))`
   - **Priority:** Medium - Better than single-line
   - **Effort:** 1 hour
   - **Status:** Partially implemented (we handle attachments differently)

9. **Content Safe Conversion** (Already Implemented)
   - Uses `msg.content_safe(&cache)` for Discord messages
   - Converts mentions to readable format
   - **Assessment:** ✅ We already use this pattern

### Patterns NOT Worth Implementing
- Ozinger FAKEMSG (network-specific)
- Rust-specific patterns (we use Python)
- Stopper pattern (we have our own shutdown logic)

### Key Insights from discord-irc-rs

**Strengths:**
- Sophisticated IRC formatting parser with state machine
- Strategic zero-width space insertion using grapheme segmentation
- Auto-detect avatars from Discord members
- Nickname normalization for protocol conflicts
- Clean async architecture with tokio
- Comprehensive formatting conversion

**Weaknesses:**
- No puppets (single bot, except ozinger FAKEMSG)
- Rust (not Python, but well-written)
- Limited to single channel pair

**Best practices to adopt:**
- IRC formatting to Discord markdown conversion (high priority)
- Strategic zero-width space insertion (high priority)
- Nickname normalization (medium priority)
- Auto-detect avatars (medium priority)
- Multi-line message handling (medium priority)

**Total estimated effort:** 17-24 hours

**Priority Assessment:**
- **Immediate:** IRC formatting conversion (8-12 hours), Strategic ZWS insertion (2-3 hours)
- **Short-term:** Auto-detect avatars (3-4 hours), Nickname normalization (1 hour), Multi-line handling (1 hour)
- **Long-term:** Bridge member changes (2-3 hours), Exit on send error (1 hour)

---

## discord-irc-sync Audit (Python) - 2026-02-19

**Repository**: Discord-IRC synchronization with user bots  
**Language**: Python 3.5+  
**Architecture**: Threading-based with notification system, spawns IRC bots per Discord user  
**Assessment**: Interesting multi-bot architecture with sophisticated formatting

### Patterns Identified

1. **✅ Cyrillic Character Substitution for Anti-Ping**
   - Replaces Latin chars with visually similar Cyrillic chars
   - Pattern: `de_hl_nick()` function
   - Substitutions: `a→а, A→А, B→В, S→Ѕ, M→М, O→О, o→о, p→р, P→Р, c→с, y→у, x→х, s→ѕ, i→і, j→ј, e→е, 0→ѳ, h→Һ`
   - Fallback: Insert apostrophe after first char if no match
   - **Priority:** Medium - Alternative to zero-width spaces
   - **Effort:** 1-2 hours
   - **Status:** Not implemented

2. **✅ Automatic Mention Conversion (IRC → Discord)**
   - Searches all Discord members and converts IRC nicks to Discord mentions
   - Pattern: `hl_nicks()` - wraps each char in brackets for case-insensitive regex
   - Converts `@nick` in IRC message to `<@user_id>` in Discord
   - Uses `client.mention` for proper Discord mentions
   - **Priority:** Medium - Better UX for cross-platform mentions
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

3. **✅ Sophisticated IRC→Discord Formatting Conversion**
   - State machine with bitwise flags (B_FLAG=0x01, I_FLAG=0x02, U_FLAG=0x04)
   - Tracks formatting state per character
   - Creates intervals of formatted text
   - Handles overlapping/nested formatting correctly
   - Orders intervals (not included > included) to avoid conflicts
   - Converts: Bold (0x02→**), Italic (0x1d→*), Underline (0x1f→__)
   - Removes IRC color codes: `\x03\d{2}(?:,\d{2})`
   - Escapes Discord markdown: `\\ ~~ _ *` at word boundaries
   - **Priority:** High - More sophisticated than discord-irc-rs
   - **Effort:** 6-10 hours (complex interval logic)
   - **Status:** Not implemented

4. **✅ Discord→IRC Formatting Conversion**
   - Regex-based conversion with proper nesting
   - Handles: `**bold**→0x02`, `*italic*→0x1d`, `__underline__→0x1f`
   - Sanitizes escaped chars: `\\([^A-Za-z0-9])→\1`
   - Configurable: `formatting.discord_to_irc = true/false`
   - **Priority:** Medium - Bidirectional formatting
   - **Effort:** 3-4 hours
   - **Status:** Not implemented

5. **✅ Per-User IRC Bot Spawning**
   - Spawns separate IRC bot thread for each Discord user
   - Tracks user bots in `users_bots` dict
   - Routes messages to correct user bot based on username
   - Spawns on Discord member status change (offline→online)
   - Kills bot on status change (online→offline)
   - **Priority:** Low - We use puppets differently
   - **Effort:** N/A (architectural difference)
   - **Status:** Not applicable (we have puppet system)

6. **✅ Notification System Architecture**
   - Event-driven notification pattern between IRC and Discord
   - Notification types: `message`, `user`, `notification`, `join`, `part`, `quit`, `kick`
   - Callback dispatch: `self.callback[notif.n_type][notif.subtype](notif)`
   - Bidirectional communication via notification objects
   - **Priority:** Low - We have event bus
   - **Effort:** N/A (we have better event system)
   - **Status:** Not applicable

7. **✅ Configurable Message Templates**
   - Template strings with placeholders: `:username:`, `:message:`
   - Config: `output_msg: "<:username:> :message:"`
   - Config: `output_cmd: "CMD by :username:"`
   - Separate templates for messages vs commands
   - **Priority:** Low - Already covered in other audits
   - **Effort:** 1-2 hours
   - **Status:** Not implemented

8. **✅ IRC Action (/me) Handling**
   - Detects IRC CTCP ACTION messages
   - Formats as: `\* **username** action_text`
   - Sends to Discord with italic formatting
   - **Priority:** Medium - Common IRC feature
   - **Effort:** 1-2 hours
   - **Status:** Not implemented

9. **✅ Configurable Event Logging**
   - Config flags: `log_events = true/false` per platform
   - Controls whether JOIN/PART/QUIT/KICK are bridged
   - Separate control for IRC and Discord
   - **Priority:** Low - Already in our config
   - **Effort:** 30 minutes
   - **Status:** Partially implemented

### Patterns NOT Worth Implementing
- Threading architecture (we use async)
- Per-user bot spawning (we have puppets)
- Notification system (we have event bus)
- Status-based bot spawning (different approach)

### Key Insights from discord-irc-sync

**Strengths:**
- Sophisticated IRC→Discord formatting with interval logic
- Cyrillic character substitution for anti-ping
- Automatic mention conversion
- Per-user IRC bot spawning (unique approach)
- Bidirectional formatting conversion
- IRC action (/me) handling

**Weaknesses:**
- Threading instead of async
- Complex bot spawning logic
- Python 3.5+ (old)
- No flood control
- No reconnection logic

**Best practices to adopt:**
- IRC→Discord formatting with interval logic (high priority)
- Cyrillic character substitution (medium priority)
- Automatic mention conversion (medium priority)
- IRC action handling (medium priority)
- Discord→IRC formatting (medium priority)

**Total estimated effort:** 13-21 hours

**Priority Assessment:**
- **Immediate:** IRC→Discord formatting (6-10 hours)
- **Short-term:** Discord→IRC formatting (3-4 hours), Mention conversion (2-3 hours), IRC action handling (1-2 hours), Cyrillic substitution (1-2 hours)
- **Long-term:** Configurable event logging (30 minutes)

---

## discord-ircv3 Audit (Go) - 2026-02-19

**Repository**: Modern IRCv3 bridge with advanced features  
**Language**: Go  
**Architecture**: Goroutines with auto-reconnect, single bot (no puppets)  
**Assessment**: Excellent IRCv3 implementation with modern features

### Patterns Identified

1. **✅ IRCv3 Typing Notifications**
   - Discord typing → IRC `TAGMSG` with `+typing: active` tag
   - Uses IRCv3 client tag: https://ircv3.net/specs/client-tags/typing.html
   - Sends typing indicator when Discord user starts typing
   - **Priority:** Medium - Nice UX feature
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

2. **✅ IRCv3 Message Replies (draft/reply)**
   - Bidirectional reply tracking using `+draft/reply` tag
   - Discord reply → IRC with `+draft/reply=<msgid>` tag
   - IRC reply → Discord MessageReference
   - Maintains message ID mappings: `idIRCDiscord` and `idDiscordIRC`
   - Strips bot mention prefix when replying: `TrimPrefix(body, fmt.Sprintf("%s: ", botNick))`
   - **Priority:** High - Already in our TODO, this shows implementation
   - **Effort:** 3-4 hours
   - **Status:** Partially implemented (we have reply tracking)

3. **✅ IRCv3 Message Deletion (draft/message-redaction)**
   - Discord delete → IRC `REDACT` command
   - IRC `REDACT` → Discord `ChannelMessageDelete`
   - Capability negotiation: `draft/message-redaction`
   - Checks capability before sending: `!ircClient.CapEnabled("draft/message-redaction")`
   - **Priority:** High - Modern IRC feature
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

4. **✅ IRCv3 Reactions (draft/react)**
   - Discord reaction → IRC `TAGMSG` with `+draft/react: <emoji>` tag
   - IRC reaction → Discord `MessageReactionAdd`
   - Requires message ID mapping to target correct message
   - **Priority:** Medium - Nice feature
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

5. **✅ Color-Coded Nicknames**
   - Uses Discord role color if available: `discord.State.MessageColor(m.Message)`
   - Fallback to user accent color: `m.Author.AccentColor`
   - Fallback to hash-based color: FNV-1a hash of username → color from valid list
   - Valid IRC colors: `[2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13]` (avoids white/black)
   - Hex color support: `\x04RRGGBB` for true color
   - **Priority:** Medium - Better visual distinction
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

6. **✅ Zero-Width Space After First Character**
   - Inserts U+200B after first Unicode rune in nickname
   - Uses `utf8.DecodeRuneInString()` for proper Unicode handling
   - Pattern: `string([]rune{r, '\u200B'}) + nick[size:]`
   - Prevents pings while keeping nick readable
   - **Priority:** Medium - Already covered in other audits
   - **Effort:** 1 hour
   - **Status:** Not implemented

7. **✅ Advanced Discord Formatting Parser**
   - Uses external library: `github.com/delthas/discord-formatting`
   - AST-based parsing with tree walker
   - Handles: Bold, Italic, Underline, Strikethrough, Code blocks, Spoilers
   - Converts Discord mentions to readable text:
     - User mentions → `@nickname`
     - Channel mentions → `#channel-name`
     - Role mentions → `@role-name`
   - Timestamp formatting with multiple styles (t, T, d, D, f, F, R)
   - Emoji conversion: Discord emoji → `:emoji_name:`
   - **Priority:** High - Professional Discord parsing
   - **Effort:** 5-8 hours (or use library)
   - **Status:** Not implemented

8. **✅ IRC→Discord Formatting with URL Preservation**
   - State machine tracking formatting per character
   - Detects URLs with regex: `^(https?://[^\s<]+[^<.,:;"')\]\s])`
   - Preserves formatting chars inside URLs (no escaping)
   - Escapes Discord markdown outside URLs: `\ * _ ~`
   - Handles raw mode (backticks) - no formatting inside code
   - Inserts zero-width space between format changes
   - Strips IRC colors: `\x03\d{2}(?:,\d{2})` and hex colors: `\x04RRGGBB`
   - **Priority:** High - Better than other implementations
   - **Effort:** 6-8 hours
   - **Status:** Not implemented

9. **✅ Media Link Embedding**
   - Detects media URLs: `.jpg|.jpeg|.png|.gif|.mp4|.webm`
   - Sends media links in separate message for Discord embedding
   - Pattern: `<bold><nick></bold>` then media URL on next line
   - Only triggers if URL is standalone (no spaces in message)
   - **Priority:** Medium - Better media display
   - **Effort:** 1-2 hours
   - **Status:** Not implemented

10. **✅ IRC→Discord Mention/Emoji Conversion**
    - Converts IRC `@username#1234` to Discord mentions
    - Searches guild members by username + discriminator
    - Fallback search by nickname, then username only
    - Role mention support: `@role-name` → Discord role mention
    - Emoji conversion: `:emoji:` → Discord custom emoji
    - Skips conversion inside backticks (code blocks)
    - **Priority:** Medium - Better cross-platform mentions
    - **Effort:** 3-4 hours
    - **Status:** Not implemented

11. **✅ BOT Mode Auto-Detection**
    - Parses IRC `005 ISUPPORT` for `BOT` parameter
    - Automatically sets `+B` mode if server supports it
    - Pattern: `MODE <nick> +<value>` where value from `BOT=<value>`
    - **Priority:** Low - IRC server feature
    - **Effort:** 1 hour
    - **Status:** Not implemented

12. **✅ Rate Limiting Configuration**
    - IRC client config: `SendLimit: 500ms`, `SendBurst: 10`
    - Allows burst of 10 messages, then 500ms delay between sends
    - Built into IRC library configuration
    - **Priority:** High - Already in our TODO
    - **Effort:** 1 hour (config-based)
    - **Status:** Not implemented

13. **✅ Ready Detection with PING/PONG**
    - Sends `PING ready` after receiving `005 ISUPPORT`
    - Waits for `PONG ready` before processing messages
    - Ensures server is fully ready before bridging
    - Pattern: `ircReady` flag
    - **Priority:** Low - Reliability improvement
    - **Effort:** 30 minutes
    - **Status:** Not implemented

14. **✅ Newline Replacement**
    - Replaces `\r\n`, `\n`, `\r` with spaces in Discord→IRC
    - Prevents multi-line IRC messages from single Discord message
    - Uses `strings.NewReplacer` for efficiency
    - **Priority:** Low - Already handle multi-line differently
    - **Effort:** 30 minutes
    - **Status:** Not applicable (we split by newline)

### Patterns NOT Worth Implementing
- Newline replacement (we split by newline instead)
- Go-specific patterns (we use Python)

### IRCv3 Dependencies (from specs)

Reply, react, and redaction require: `message-tags`, `message-ids`, `echo-message`. Ensure these caps are negotiated before implementing.

### Key Insights from discord-ircv3

**Strengths:**
- Excellent IRCv3 support (typing, replies, redaction, reactions)
- Advanced Discord formatting parser with AST
- Color-coded nicknames with fallback chain
- URL-aware formatting (preserves chars in URLs)
- Media link embedding
- Bidirectional mention/emoji conversion
- Rate limiting built into IRC client
- Clean Go implementation with goroutines

**Weaknesses:**
- No puppets (single bot)
- Go (not Python, but well-written)
- Limited to single channel pair

**Best practices to adopt:**
- IRCv3 typing notifications (medium priority)
- IRCv3 message deletion/redaction (high priority)
- IRCv3 reactions (medium priority)
- Color-coded nicknames (medium priority)
- Advanced Discord formatting parser (high priority)
- URL-aware formatting (high priority)
- Media link embedding (medium priority)
- Mention/emoji conversion (medium priority)
- Rate limiting config (high priority)

**Total estimated effort:** 30-42 hours

**Priority Assessment:**
- **Immediate:** IRCv3 message deletion (2-3 hours), URL-aware formatting (6-8 hours), Advanced Discord parser (5-8 hours), Rate limiting (1 hour)
- **Short-term:** IRCv3 replies implementation (3-4 hours), Color-coded nicks (2-3 hours), Mention/emoji conversion (3-4 hours), Typing notifications (2-3 hours), Reactions (2-3 hours), Media embedding (1-2 hours)
- **Long-term:** BOT mode detection (1 hour), Ready detection (30 minutes)

---

## discord-xmpp-bridge Audit (JavaScript) - 2026-02-19

**Repository**: Discord-XMPP bridge with avatar spoofing  
**Language**: JavaScript (Node.js)  
**Architecture**: Event-driven with Redis cache, webhook-based  
**Assessment**: Interesting XMPP-specific patterns, but limited scope

### Patterns Identified

1. **✅ XMPP VCard Avatar Fetching**
   - Monitors XMPP presence stanzas for `vcard-temp:x:update` namespace
   - Extracts avatar hash from `<photo>` element
   - Fetches full VCard using IQ stanza when hash changes
   - Retrieves avatar from `PHOTO.BINVAL` (base64) and `PHOTO.TYPE` (MIME)
   - Caches avatar hash per user to avoid redundant fetches
   - **Priority:** Medium - XMPP avatar support
   - **Effort:** 3-4 hours
   - **Status:** Not implemented

2. **✅ Avatar Dominant Color Extraction**
   - Uses ImageMagick to extract dominant color from avatar
   - Scales image to 1x1 pixel and gets RGB value
   - Converts RGB to hex color code
   - Pattern: `convert image -scale 1x1! -format '%[pixel:u]' info:-`
   - Stores color in cache for webhook embeds
   - **Priority:** Low - Nice visual feature
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

3. **✅ Pomf File Upload for Avatars**
   - Uploads XMPP avatars to Pomf-compatible file host
   - Converts base64 avatar data to file
   - Uses FormData multipart upload
   - Stores public URL for Discord webhooks
   - Pattern: External file hosting for cross-platform avatars
   - **Priority:** Low - We can use Discord CDN
   - **Effort:** N/A (not applicable)
   - **Status:** Not applicable

4. **✅ Redis-Based Bridge Mapping**
   - Stores guild↔MUC mappings in Redis hashes
   - Keys: `guildtomuc`, `muctoguild`, `guildtochannel`
   - Bidirectional lookups for routing
   - Persistent storage across restarts
   - **Priority:** Low - We use YAML config
   - **Effort:** N/A (architectural difference)
   - **Status:** Not applicable

5. **✅ XMPP MUC Join with History Limit**
   - Joins MUC with `<history maxchars="0"/>` to skip backlog
   - Pattern: `<presence to="room@muc/nick"><x xmlns="http://jabber.org/protocol/muc"><history maxchars="0"/></x></presence>`
   - Prevents flooding bridge with old messages on connect
   - **Priority:** Medium - Already in our TODO
   - **Effort:** 30 minutes
   - **Status:** Not implemented

6. **✅ XMPP Stanza-ID for Message Tracking**
   - Uses `<stanza-id>` element for message identification
   - Pattern: `stanza.getChild('stanza-id').attrs.by`
   - Tracks messages for routing and deduplication
   - **Priority:** Medium - XMPP message tracking
   - **Effort:** 1-2 hours
   - **Status:** Not implemented

7. **✅ Channel Prefix Convention**
   - Sends init message to channels starting with "bot"
   - Pattern: `channel.name.startsWith('bot')`
   - Convention for bot-specific channels
   - **Priority:** Low - Configuration-based approach better
   - **Effort:** N/A (not applicable)
   - **Status:** Not applicable

8. **✅ Discord Clean Content Usage**
   - Uses `msg.cleanContent` for Discord messages
   - Converts mentions to readable format
   - **Priority:** Already implemented
   - **Effort:** N/A
   - **Status:** ✅ Already implemented

9. **✅ Attachment URL Appending**
   - Appends attachment URLs to message content
   - Pattern: `${msg.cleanContent} ${msg.attachments.map(a => a.url).join(' ')}`
   - **Priority:** Already implemented
   - **Effort:** N/A
   - **Status:** ✅ Already implemented

### Patterns NOT Worth Implementing
- Pomf file upload (we use Discord CDN)
- Redis bridge mapping (we use YAML config)
- Channel prefix convention (config-based better)
- Bot init messages (not needed)

### Key Insights from discord-xmpp-bridge

**Strengths:**
- XMPP VCard avatar fetching
- Avatar dominant color extraction
- XMPP stanza-id tracking
- MUC join with history limit
- Redis-based persistence

**Weaknesses:**
- JavaScript (not Python)
- Limited feature set
- No IRC support
- Requires external file hosting (Pomf)
- No formatting conversion
- No puppets/multi-presence

**Best practices to adopt:**
- XMPP VCard avatar fetching (medium priority)
- MUC join with history limit (medium priority)
- XMPP stanza-id tracking (medium priority)
- Avatar dominant color extraction (low priority)

**Total estimated effort:** 6.5-9.5 hours

**Priority Assessment:**
- **Immediate:** None
- **Short-term:** XMPP VCard avatars (3-4 hours), Stanza-ID tracking (1-2 hours), MUC history limit (30 minutes)
- **Long-term:** Avatar color extraction (2-3 hours)

**Note:** This bridge is XMPP-focused with limited features. Most valuable patterns are XMPP-specific (VCard avatars, stanza-id tracking, MUC history). Since we already have XMPP component support, these patterns are relevant but lower priority than IRC features.

---

## dpytest Testing Library Audit - 2026-02-19

**Repository**: Testing framework for discord.py bots  
**Language**: Python  
**Purpose**: Unit testing Discord bots without connecting to Discord API  
**Assessment**: Valuable patterns for improving our test suite

### Testing Patterns Identified

1. **✅ Mock Discord State/Backend**
   - Replaces `ConnectionState` with mock implementation
   - Intercepts Discord API calls without network requests
   - Pattern: `FakeState` class overrides `discord.state.ConnectionState`
   - Allows testing bot behavior in isolation
   - **Priority:** High - Improve test speed and reliability
   - **Effort:** 8-12 hours (significant refactoring)
   - **Status:** Not implemented

2. **✅ Factory Pattern for Discord Objects**
   - `make_user_dict()`, `make_member_dict()`, `make_message_dict()`, etc.
   - Creates valid Discord API JSON structures
   - Generates realistic snowflake IDs with timestamp encoding
   - Pattern: `make_id()` generates Discord-compatible IDs
   - **Priority:** High - Better test fixtures
   - **Effort:** 4-6 hours
   - **Status:** Partially implemented (we create objects manually)

3. **✅ Fluent Assertion API (Verify Pattern)**
   - Chainable verification: `verify().message().content("text")`
   - Builder pattern for test assertions
   - Methods: `.contains()`, `.peek()`, `.nothing()`, `.embed()`, `.attachment()`
   - Returns boolean for `assert` statements
   - **Priority:** Medium - Better test readability
   - **Effort:** 6-8 hours
   - **Status:** Not implemented

4. **✅ Message Queue for Sent Messages**
   - `PeekableQueue` tracks all sent messages
   - `.peek()` inspects without removing from queue
   - `.get_nowait()` retrieves and removes message
   - Allows testing message order and content
   - **Priority:** High - Already have similar pattern
   - **Effort:** 2-3 hours (refinement)
   - **Status:** Partially implemented

5. **✅ Async Event Runner**
   - `run_all_events()` waits for all Discord events to complete
   - Tracks `_run_event` tasks and waits for completion
   - Ensures event handlers finish before assertions
   - Pattern: Polls `asyncio.all_tasks()` for pending events
   - **Priority:** High - Prevent race conditions in tests
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

6. **✅ Configuration Decorator**
   - `@require_config` enforces setup before test execution
   - Raises `RuntimeError` if runner not configured
   - Pattern: Decorator checks global config state
   - **Priority:** Low - Test infrastructure
   - **Effort:** 1 hour
   - **Status:** Not implemented

7. **✅ Mock HTTP Client**
   - `FakeHttp` replaces `discord.http.HTTPClient`
   - Intercepts API calls and returns fake responses
   - No network requests during tests
   - **Priority:** High - Fast, isolated tests
   - **Effort:** 6-8 hours
   - **Status:** Not implemented

8. **✅ Pytest Fixtures for Bot Setup**
   - Automatic bot configuration per test
   - Guild/channel/member creation
   - Pattern: `@pytest.fixture` with `dpytest.configure()`
   - **Priority:** Medium - Test convenience
   - **Effort:** 2-3 hours
   - **Status:** Partially implemented

9. **✅ Attachment Factory**
   - `make_attachment_dict()` creates attachment objects
   - Includes URL, size, dimensions, content type
   - Pattern: Realistic attachment data for testing
   - **Priority:** Medium - Test file handling
   - **Effort:** 1-2 hours
   - **Status:** Not implemented

10. **✅ Error Queue for Command Errors**
    - Separate queue for `CommandError` exceptions
    - Tracks errors with context
    - Pattern: `error_queue: PeekableQueue[tuple[Context, CommandError]]`
    - **Priority:** Medium - Test error handling
    - **Effort:** 2-3 hours
    - **Status:** Not implemented

### Key Insights from dpytest

**Strengths:**
- Complete Discord API mocking
- No network requests needed for tests
- Fluent assertion API
- Factory pattern for test data
- Async event synchronization
- Fast test execution

**Weaknesses:**
- Specific to discord.py (not directly applicable to our multi-protocol bridge)
- Requires significant setup
- Mock state can diverge from real Discord behavior

**Best practices to adopt:**
- Factory pattern for creating test objects (high priority)
- Async event runner to prevent race conditions (high priority)
- Message queue with peek functionality (high priority)
- Fluent assertion API for readability (medium priority)
- Mock HTTP client for isolated tests (high priority)
- Error queue for testing error handling (medium priority)

**Total estimated effort:** 34-50 hours

**Priority Assessment:**
- **Immediate:** Factory pattern (4-6 hours), Async event runner (2-3 hours), Message queue refinement (2-3 hours)
- **Short-term:** Mock HTTP client (6-8 hours), Mock Discord state (8-12 hours), Fluent assertions (6-8 hours)
- **Long-term:** Error queue (2-3 hours), Attachment factory (1-2 hours), Pytest fixtures (2-3 hours), Config decorator (1 hour)

**Note:** dpytest is a testing library, not a bridge. These patterns are valuable for improving our test suite quality, speed, and maintainability. The factory pattern and async event runner are particularly valuable for preventing flaky tests.

---

## DRC (Discord Relay Chat) Audit - 2026-02-19

**Repository**: Full-featured IRC client using Discord as UI  
**Language**: JavaScript (Node.js)  
**Architecture**: Multi-process (discord.js, irc.js, http.js) with Redis IPC  
**Assessment**: Production IRC client, not a bridge - limited relevance

### Patterns Identified

1. **✅ Auto-Creating PM Channels**
   - Creates Discord channel for each IRC private message
   - Category name matching: `/priv(?:ate)?\s*me?s(?:sa)?ge?s?/ig` or "PMs"
   - Pattern: Traditional IRC "query window" feature
   - Expires stale PM channels after configurable time
   - Uses Redis keyspace notifications for expiry
   - **Priority:** Low - We handle PMs differently
   - **Effort:** 4-6 hours
   - **Status:** Not applicable (architectural difference)

2. **✅ Redis-Based IPC Between Processes**
   - Pub/sub for inter-process communication
   - Pattern: `discord.js`, `irc.js`, `http.js` as separate processes
   - Scoped Redis keys with prefix: `${NAME}-${ENV}`
   - Hot reload via C2 messages: `__c2::irc:reload`
   - **Priority:** Low - We use single process with event bus
   - **Effort:** N/A (architectural difference)
   - **Status:** Not applicable

3. **✅ Dynamic Module Reloading**
   - Hot reload handlers without restart
   - Pattern: `delete require.cache[require.resolve(path)]`
   - Triggered via Redis C2 messages
   - **Priority:** Low - Development convenience
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

4. **✅ Prometheus Metrics Integration**
   - Exports metrics for monitoring
   - Counters: `msgRxCounter`, `msgRxCounterWithType`, `eventsCounterWithType`
   - Pattern: Prometheus client library
   - **Priority:** Low - Monitoring infrastructure
   - **Effort:** 3-4 hours
   - **Status:** Not implemented

5. **✅ SQLite Log Storage with Full-Text Search**
   - Stores all IRC messages in SQLite
   - Query builder for complex searches
   - Pattern: `queryBuilder(options, fromTime, toTime)`
   - Supports: nick, ident, hostname, message content, time range
   - **Priority:** Medium - Better than file-based logs
   - **Effort:** 8-12 hours
   - **Status:** Not implemented (we use file logs)

6. **✅ HTTP Server for Log Viewing**
   - Web interface for browsing logs
   - Multiple templates: retro, nord, neon, terminal themes
   - Live log streaming via WebSocket
   - AI query integration (GPT, Claude)
   - **Priority:** Low - Nice feature but not core
   - **Effort:** 15-20 hours
   - **Status:** Not implemented

7. **✅ User Command History Tracking**
   - Tracks all user commands in SQLite
   - Pattern: `UCHistory.query()` with filters
   - Useful for debugging and auditing
   - **Priority:** Low - Debugging feature
   - **Effort:** 3-4 hours
   - **Status:** Not implemented

8. **✅ Sentiment Analysis on Messages**
   - Analyzes message sentiment scores
   - Pattern: `attachSentimentToMessages()`, `averageSentiments()`
   - Used in digest views
   - **Priority:** Low - Analytics feature
   - **Effort:** 4-6 hours
   - **Status:** Not implemented

9. **✅ Message Plotting/Visualization**
   - Plots messages per minute (MPM) graphs
   - Pattern: `plotMpmData()` generates PNG charts
   - Tracks activity over time
   - **Priority:** Low - Analytics feature
   - **Effort:** 3-4 hours
   - **Status:** Not implemented

10. **✅ Allowed Speakers Role**
    - Discord role controls who can send IRC messages
    - Pattern: `config.app.allowedSpeakersRoleId`
    - Security/access control
    - **Priority:** Low - We're single-user focused
    - **Effort:** 1-2 hours
    - **Status:** Not implemented

### Patterns NOT Worth Implementing
- Multi-process architecture (we use single process)
- Redis IPC (we use event bus)
- Auto-creating PM channels (architectural difference)
- HTTP log viewer (nice but not core)
- AI integration (out of scope)
- Sentiment analysis (out of scope)
- Message plotting (out of scope)

### Key Insights from DRC

**Strengths:**
- Production-ready IRC client
- Comprehensive logging with SQLite
- Web interface for logs
- Multi-process architecture for stability
- Extensive monitoring/metrics
- Feature-rich (AI, plotting, sentiment analysis)

**Weaknesses:**
- Not a bridge (IRC client using Discord as UI)
- JavaScript (not Python)
- Complex multi-process setup
- Over-engineered for our use case
- Many features out of scope

**Best practices to adopt:**
- SQLite log storage with query builder (medium priority)
- Dynamic module reloading (low priority)
- Prometheus metrics (low priority)

**Total estimated effort:** 8-12 hours (SQLite logs only)

**Priority Assessment:**
- **Immediate:** None
- **Short-term:** SQLite log storage (8-12 hours)
- **Long-term:** Dynamic reloading (2-3 hours), Prometheus metrics (3-4 hours)

**Note:** DRC is a full IRC client using Discord as a UI, not a bridge. Most features are out of scope for our bridge use case. The SQLite log storage pattern is the most relevant takeaway.

---

## emulsion Audit - 2026-02-19

**Repository**: Telegram-XMPP bridge  
**Language**: F# (.NET)  
**Architecture**: .NET application with SQLite database  
**Assessment**: Not relevant - different protocols and language

### Key Features (Not Applicable)

1. **Telegram Content Proxy**
   - Proxies Telegram media through own server
   - Generates hashids for content URLs
   - File caching with size limits
   - **Priority:** N/A - Telegram-specific

2. **Message Archive with SQLite**
   - Stores all messages in SQLite database
   - Automatic migrations on startup
   - **Priority:** N/A - Already covered in DRC audit

3. **XMPP Ping Support**
   - Configurable ping interval and timeout
   - **Priority:** N/A - We have XMPP stream management

4. **Message Thread Support**
   - Telegram message thread filtering
   - **Priority:** N/A - Telegram-specific

### Key Insights

**Note:** emulsion is a Telegram-XMPP bridge in F#. It has no relevant patterns for our IRC-Discord-XMPP Python bridge. The content proxy and message archive patterns were already covered in other audits.

---

## go-discord-irc Audit (Go) - 2026-02-19

**Repository**: Discord-IRC bridge with puppets  
**Language**: Go  
**Architecture**: One IRC connection per Discord user (puppets)  
**Assessment**: Mature puppet-based bridge, similar to our approach

### Patterns Identified

1. **✅ Puppet Cooldown/Idle Timeout**
   - Disconnects idle puppets after configurable duration
   - Default: 24 hours (86400 seconds)
   - Pattern: `cooldown_duration` config option
   - **Priority:** High - Already in our TODO
   - **Effort:** 2-3 hours
   - **Status:** Partially implemented (we have 24h default)

2. **✅ WEBIRC Support**
   - Uses WEBIRC for distinct hostnames per Discord user
   - Pattern: `webirc_pass` config option
   - Gives each puppet a unique hostname
   - **Priority:** High - Already covered in CatPuppetBridge audit
   - **Effort:** 3-4 hours
   - **Status:** Not implemented

3. **✅ Pre-Join Commands**
   - Executes commands before joining channels
   - Separate commands for listener and puppets
   - Pattern: `irc_listener_prejoin_commands`, `irc_puppet_prejoin_commands`
   - Default puppet command: `MODE ${NICK} +D` (deaf mode)
   - **Priority:** Medium - Useful for NickServ, modes
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

4. **✅ Connection Limit**
   - Limits total IRC connections (including listener)
   - Pattern: `connection_limit` config option
   - 0 or less = unlimited
   - **Priority:** Medium - Resource management
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

5. **✅ Allowed/Ignored Discord Users**
   - `allowed_discord_ids`: Whitelist of Discord users to bridge
   - `ignored_discord_ids`: Blacklist of Discord users
   - Pattern: String slice of Discord IDs
   - **Priority:** Medium - Access control
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

6. **✅ IRC Hostmask Filtering**
   - Ignores IRC users by hostmask pattern
   - Uses glob matching: `ignored_irc_hostmasks`
   - Pattern: `github.com/gobwas/glob` library
   - **Priority:** Medium - Filter bots/services
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

7. **✅ Message Content Filtering**
   - `irc_message_filter`: Ignore IRC messages matching patterns
   - `discord_message_filter`: Ignore Discord messages matching patterns
   - Pattern: String slice of filter patterns
   - **Priority:** Low - Content filtering
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

8. **✅ Hot-Reloadable Configuration**
   - Uses `fsnotify` to watch config file changes
   - Automatically updates channel mappings without restart
   - Pattern: Viper config library with file watching
   - **Priority:** Low - Development convenience
   - **Effort:** 3-4 hours
   - **Status:** Not implemented

9. **✅ Configurable Avatar URL Template**
   - Template for generating avatar URLs
   - Default: `https://robohash.org/${USERNAME}.png?set=set4`
   - Pattern: String template with `${USERNAME}` placeholder
   - **Priority:** Low - Already covered in other audits
   - **Effort:** 1 hour
   - **Status:** Not implemented

10. **✅ Max Nick Length Configuration**
    - Configurable maximum nickname length
    - Default: 30 characters
    - Pattern: `max_nick_length` config option
    - **Priority:** Low - IRC server compatibility
    - **Effort:** 1 hour
    - **Status:** Not implemented

11. **✅ Nickname Suffix and Separator**
    - `suffix`: Appended to Discord usernames (default: `~d`)
    - `separator`: Used in fallback situations (default: `_`)
    - Pattern: Configurable strings for nick generation
    - Example: `bob_7247_d` (username + discriminator + suffix)
    - **Priority:** Medium - Already in our TODO
    - **Effort:** 1-2 hours
    - **Status:** Partially implemented

12. **✅ Show Join/Quit Messages**
    - Configurable display of JOIN/PART/QUIT/KICK on Discord
    - Pattern: `show_joinquit` boolean config
    - **Priority:** Low - Already in our TODO
    - **Effort:** 1 hour
    - **Status:** Not implemented

### Key Insights from go-discord-irc

**Strengths:**
- Mature puppet-based architecture (similar to ours)
- Hot-reloadable configuration
- Comprehensive access control (allowed/ignored users)
- WEBIRC support for distinct hostnames
- Pre-join commands for flexibility
- Connection limiting for resource management

**Weaknesses:**
- Go (not Python)
- No XMPP support
- Requires custom IRC server config for best experience

**Best practices to adopt:**
- Puppet cooldown/idle timeout (high priority)
- WEBIRC support (high priority)
- Pre-join commands (medium priority)
- Connection limit (medium priority)
- Allowed/ignored users (medium priority)
- IRC hostmask filtering (medium priority)
- Hot-reloadable config (low priority)

**Total estimated effort:** 21-31 hours

**Priority Assessment:**
- **Immediate:** Puppet cooldown (2-3 hours), WEBIRC (3-4 hours)
- **Short-term:** Pre-join commands (2-3 hours), Connection limit (2-3 hours), Allowed/ignored users (2-3 hours), Hostmask filtering (2-3 hours), Nick suffix/separator (1-2 hours)
- **Long-term:** Message filtering (2-3 hours), Hot-reload config (3-4 hours), Max nick length (1 hour), Show join/quit (1 hour), Avatar URL template (1 hour)

**Note:** go-discord-irc uses a similar puppet-based architecture to ours. Many patterns are already in our TODO or partially implemented. The most valuable additions are puppet cooldown, WEBIRC, and pre-join commands.

---

## koishi Audit (Python) - 2026-02-19

**Repository**: Matrix-XMPP bridge with puppeting  
**Language**: Python  
**Architecture**: slixmpp component with PostgreSQL database  
**Assessment**: Early development, Matrix-focused, limited relevance

### Patterns Identified

1. **✅ Async Event for Join Coordination**
   - Uses `asyncio.Event` to prevent duplicate joins
   - Pattern: `is_joining: dict[str, asyncio.Event]`
   - Waits for in-progress joins before proceeding
   - **Priority:** Medium - Prevents race conditions
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

2. **✅ Background Task Set**
   - Tracks background tasks to prevent garbage collection
   - Pattern: `background_tasks = set()`
   - Keeps task references alive
   - **Priority:** Low - Python best practice
   - **Effort:** 1 hour
   - **Status:** Not implemented

3. **✅ Deduplication Sets**
   - Uses sets to track bridged messages
   - Pattern: `bridged_jnics`, `bridged_jids`, `bridged_mx_eventid`
   - **Priority:** N/A - Already implemented
   - **Status:** ✅ Already implemented

4. **PostgreSQL for Message Storage** (Not Applicable)
   - Uses PostgreSQL instead of SQLite
   - **Priority:** N/A - We use file-based logs

5. **Fake Auth Media Redirect** (Not Applicable)
   - Matrix-specific media handling
   - **Priority:** N/A - Different approach

### Key Insights from koishi

**Strengths:**
- Python implementation (same as ours)
- XMPP component with puppeting
- Async event coordination

**Weaknesses:**
- Very early development
- Matrix-XMPP (not IRC-Discord)
- Hardcoded values (not production-ready)
- Limited features

**Best practices to adopt:**
- Async event for join coordination (medium priority)
- Background task set (low priority)

**Total estimated effort:** 2-4 hours

**Priority Assessment:**
- **Immediate:** None
- **Short-term:** Async event for join coordination (2-3 hours)
- **Long-term:** Background task set (1 hour)

**Note:** koishi is a Matrix-XMPP bridge in early development. The async event pattern for preventing duplicate joins is the only relevant takeaway.

---

## mod_muc_irc Audit (Lua) - 2026-02-19

**Repository**: Prosody XMPP module for IRC bridging  
**Language**: Lua  
**Architecture**: Prosody module with per-user IRC connections  
**Assessment**: Server-side module, different architecture, limited relevance

### Patterns Identified

1. **✅ Per-User IRC Connections**
   - Each XMPP user gets separate IRC connection
   - Pattern: `occupant_jid_to_conn` mapping
   - Similar to our puppet approach
   - **Priority:** N/A - Already implemented
   - **Status:** ✅ Already implemented

2. **✅ Room Name Validation**
   - Requires IRC channel names to start with `#`
   - Pattern: `if not event.stanza.to:match "^#" then`
   - Returns error for invalid room names
   - **Priority:** Low - Input validation
   - **Effort:** 30 minutes
   - **Status:** Not implemented

3. **✅ Private Message Support**
   - Allows XMPP users to PM IRC users directly
   - Pattern: Routes non-groupchat messages to IRC
   - Uses `conn:sendChat(to, body)` for PMs
   - **Priority:** Medium - Already in our TODO
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

4. **✅ Synchronous Join Waiting**
   - Blocks until IRC join completes
   - Pattern: `while not joined do cqueues.poll(conn); conn:think() end`
   - Uses cqueues for async I/O
   - **Priority:** Low - We use async/await
   - **Effort:** N/A (architectural difference)
   - **Status:** Not applicable

5. **✅ Topic Synchronization**
   - Syncs IRC topic to XMPP MUC subject
   - Pattern: `room:set_subject(nil, topic)`
   - Includes topic creator and timestamp
   - **Priority:** Medium - Already in our TODO
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

6. **✅ Nick Change Handling**
   - Detects IRC nick changes
   - Pattern: `OnNickChange` hook
   - Sends presence updates to XMPP
   - **Priority:** Low - Already covered in other audits
   - **Effort:** 2-3 hours
   - **Status:** Not implemented

7. **✅ Connection Cleanup on Disconnect**
   - Removes connection from map on disconnect
   - Pattern: `OnDisconnect` hook clears `occupant_jid_to_conn`
   - **Priority:** High - Already implemented
   - **Effort:** N/A
   - **Status:** ✅ Already implemented

8. **✅ MUC History Suppression**
   - Sets `maxchars="0"` in MUC presence
   - Pattern: `<history xmlns="..." maxchars="0"/>`
   - Prevents backlog on join
   - **Priority:** Medium - Already covered in other audits
   - **Effort:** 30 minutes
   - **Status:** Not implemented

### Patterns NOT Worth Implementing
- Synchronous join waiting (we use async/await)
- Lua-specific patterns
- Prosody module architecture
- cqueues I/O library

### Key Insights from mod_muc_irc

**Strengths:**
- Server-side XMPP module
- Per-user IRC connections (like our puppets)
- Topic synchronization
- Private message support

**Weaknesses:**
- Lua (not Python)
- Prosody-specific
- Synchronous blocking patterns
- Different architecture (server module vs standalone bridge)

**Best practices to adopt:**
- Room name validation (low priority)
- Private message support (medium priority)
- Topic synchronization (medium priority)

**Total estimated effort:** 4.5-6.5 hours

**Priority Assessment:**
- **Immediate:** None
- **Short-term:** Private message support (2-3 hours), Topic sync (2-3 hours)
- **Long-term:** Room name validation (30 minutes), MUC history suppression (30 minutes)

**Note:** mod_muc_irc is a Prosody XMPP module in Lua. It uses a similar per-user connection approach to our puppets. Most patterns are either already implemented or covered in other audits. The main takeaways are private message support and topic synchronization.

---

## out-of-your-element Audit - 2026-02-19

**Repository**: Matrix-Discord appservice bridge  
**Language**: JavaScript (Node.js)  
**Architecture**: Matrix appservice with SQLite database  
**Assessment**: Not relevant - Matrix-Discord bridge, no IRC

### Key Features (Not Applicable)

1. **Matrix Appservice Architecture**
   - Uses Matrix appservice protocol
   - Not applicable to our IRC-Discord-XMPP bridge

2. **PluralKit Integration**
   - Each PluralKit member gets persistent account
   - Restyled replies for PluralKit members
   - **Priority:** N/A - Discord bot specific

3. **Simulated User Accounts**
   - Named `@username` instead of `@112233445566778899`
   - **Priority:** N/A - Already implemented (we use puppets)

4. **Matrix Custom Emoji Sprite Sheets**
   - Private room emojis visible on Discord as sprite sheet
   - **Priority:** N/A - Matrix-specific

5. **File Size Optimization**
   - Links larger files instead of reuploading
   - **Priority:** N/A - Different approach

### Key Insights

**Strengths:**
- Modern Matrix-Discord bridge
- Efficient (memory, database, algorithms)
- Comprehensive test suite
- No locking algorithm needed
- Latest Discord API

**Weaknesses:**
- JavaScript (not Python)
- Matrix-Discord (not IRC)
- No puppetting support
- No DM support
- Not applicable to our use case

**Best practices to adopt:**
- None - different protocols and architecture

**Total estimated effort:** 0 hours (not applicable)

**Note:** out-of-your-element is a Matrix-Discord appservice bridge in JavaScript. It has no relevant patterns for our IRC-Discord-XMPP Python bridge as it focuses on Matrix instead of IRC.

---

## renostr Audit - 2026-02-19

**Repository**: Nostr-XMPP bridge  
**Language**: TypeScript  
**Architecture**: XMPP component + Nostr client  
**Assessment**: Not relevant - Nostr protocol, pre-alpha, different use case

### Key Features (Not Applicable)

1. **Nostr Protocol Bridge**
   - Bridges Nostr (decentralized social protocol) to XMPP
   - Translates Nostr notes to XEP-0277 microblogging stanzas
   - **Priority:** N/A - Nostr-specific

2. **PubSub-Based Architecture**
   - Uses XMPP PubSub for message distribution
   - Global and per-user PubSub nodes
   - **Priority:** N/A - Different architecture

3. **Private Key Management**
   - Requires access to Nostr private key for signing
   - **Priority:** N/A - Nostr-specific

### Key Insights

**Strengths:**
- XMPP component architecture
- PubSub-based message distribution
- TypeScript implementation

**Weaknesses:**
- Pre-alpha/WIP status
- Nostr protocol (not IRC/Discord)
- TypeScript (not Python)
- Requires private key access
- Not applicable to our use case

**Best practices to adopt:**
- None - different protocol (Nostr) and architecture

**Total estimated effort:** 0 hours (not applicable)

**Note:** renostr is a Nostr-XMPP bridge in pre-alpha status. Nostr is a decentralized social protocol, completely different from IRC/Discord. No relevant patterns for our bridge.

---

## Matterbridge Audit (Go) - 2026-02-19

**Repository**: Multi-protocol chat bridge  
**Language**: Go  
**Architecture**: Gateway-based with multiple protocol adapters  
**Assessment:** Mature multi-protocol bridge, key patterns already extracted

### Patterns Already Documented in TODO.md

1. **✅ IRC Flood Control** (High Priority)
   - Message queue with configurable delay
   - Token bucket algorithm
   - Prevents rate limiting and connection drops
   - **Status:** Documented in TODO.md, not implemented

2. **✅ IRC Rejoin Logic** (High Priority)
   - Automatic rejoin after KICK/disconnect
   - Configurable rejoin delay
   - **Status:** Documented in TODO.md, not implemented

3. **✅ Nick Sanitization** (High Priority)
   - Sanitizes Discord usernames for IRC compatibility
   - **Status:** Documented in TODO.md, not implemented

4. **✅ Discord Message Splitting** (Medium Priority)
   - Splits at 1950 characters
   - **Status:** Documented in TODO.md, not implemented

5. **✅ Discord Mention Control** (Medium Priority)
   - Uses AllowedMentions API
   - **Status:** Documented in TODO.md, not implemented

6. **✅ Discord Member Caching** (Medium Priority)
   - Caches for performance
   - **Status:** Documented in TODO.md, not implemented

### Key Insights from Matterbridge

**Strengths:**
- Mature, production-ready
- Supports 15+ protocols
- Gateway-based architecture
- Extensive configuration options
- Active development and community

**Weaknesses:**
- Go (not Python)
- Complex codebase due to multi-protocol support
- More features than we need

**Best practices already adopted:**
- All key patterns extracted and documented in TODO.md
- IRC flood control (token bucket)
- IRC rejoin logic
- Nick sanitization
- Discord message splitting
- Discord mention control
- Discord member caching

**Total estimated effort:** Already documented (15-20 hours for all Matterbridge patterns)

**Note:** Matterbridge is a mature multi-protocol bridge in Go. The key patterns relevant to our IRC-Discord bridge have already been extracted and documented at the top of TODO.md as high-priority items. No additional audit needed.
