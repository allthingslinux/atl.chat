---
name: Add IRC Message Flow Logging
overview: Add INFO-level logs at key points in the Discord→IRC message flow so users can trace messages without running with -v. This will help diagnose why messages may not appear to reach IRC.
todos: []
isProject: false
---

# Add IRC Message Flow Logging

## Problem

At default log level (INFO), there are no logs when:

- Discord receives a message and publishes to the bus
- Relay forwards a message to IRC
- IRC queues or sends a message

Only DEBUG-level logs exist (e.g. "IRC send skipped", "Relay: no mapping"), which require `bridge -v` to see. The user cannot trace message flow without verbose mode.

## Current Flow (no INFO logs)

```mermaid
flowchart LR
    Discord[Discord _on_message] -->|publish MessageIn| Relay[Relay]
    Relay -->|publish MessageOut| IRC[IRC push_event]
    IRC -->|queue_message| Client[IRCClient]
    Client -->|_send_message| RawMsg[rawmsg RELAYMSG]
```



- **Discord**: No log when receiving; silently returns if channel not bridged
- **Relay**: Only `logger.debug("Relay: no mapping...")` when mapping fails
- **IRC**: Only `logger.debug("IRC send skipped...")` or `logger.warning("IRC MessageOut dropped...")` when failing; no log on success

## Proposed Changes

### 1. Discord adapter — log when message is bridged

**File:** [apps/bridge/src/bridge/adapters/disc.py](apps/bridge/src/bridge/adapters/disc.py)

In `_on_message`, after `_is_bridged_channel` check and before `self._bus.publish`:

- Add `logger.info("Discord message bridged: channel={} author={}", channel_id, message.author.display_name)` — only when we actually publish (so we know the message was accepted for bridging)

### 2. Relay — log when forwarding to IRC

**File:** [apps/bridge/src/bridge/gateway/relay.py](apps/bridge/src/bridge/gateway/relay.py)

In `push_event`, inside the `for target in self.TARGETS` loop, when `target == "irc"` and we're about to `self._bus.publish`:

- Add `logger.info("Relay: discord -> irc channel={}", channel_id)` — only when we actually publish (so we know the relay forwarded to IRC)

### 3. IRC adapter — log when we queue/send

**File:** [apps/bridge/src/bridge/adapters/irc.py](apps/bridge/src/bridge/adapters/irc.py)

- In `push_event` when we call `self._client.queue_message(evt)`: add `logger.info("IRC: queued message for channel={}", evt.channel_id)`
- In `_send_message` after successful send (inside the loop, after rawmsg): add `logger.info("IRC: sent RELAYMSG to {} as {}", target, spoofed_nick)` — only once per message (first chunk), not per chunk

### 4. Upgrade relay "no mapping" to WARNING

**File:** [apps/bridge/src/bridge/gateway/relay.py](apps/bridge/src/bridge/gateway/relay.py)

Change `logger.debug("Relay: no mapping...")` to `logger.warning("Relay: no mapping for {} channel {}", evt.origin, evt.channel_id)` so users see when messages are dropped due to missing channel mapping.

### 5. Upgrade IRC "send skipped" to WARNING

**File:** [apps/bridge/src/bridge/adapters/irc.py](apps/bridge/src/bridge/adapters/irc.py)

Change `logger.debug("IRC send skipped: no mapping...")` to `logger.warning("IRC send skipped: no mapping for channel {}", evt.channel_id)` so users see when IRC drops a message.

## Expected Result

With default INFO level, when sending a message from Discord:

- `Discord message bridged: channel=... author=...`
- `Relay: discord -> irc channel=...`
- `IRC: queued message for channel=...`
- `IRC: sent RELAYMSG to #general as Alice`

If any step fails:

- `Relay: no mapping for discord channel ...` (WARNING)
- `IRC send skipped: no mapping for channel ...` (WARNING)
- `IRC MessageOut dropped: no client (channel=...)` (WARNING, already exists)

## Log Volume

One INFO log per message per hop (Discord → Relay → IRC queue → IRC send) = 4 lines per message. Acceptable for debugging. If too noisy later, we can add a config flag to disable message flow logs.
