---
summary: Module for improving the life of bot authors
---

This module makes it easier to write MUC bots by removing the
requirement that the bot be online and joined to the room.

All the bot needs to do is send a message and this module handles the
rest.

# Configuration

Example configuration in Prosody:

```lua
Component "muc.example.com" "muc"

modules_enabled = {
    "muc_bot",
}
known_bots = { "bot@example.com" }
bots_get_messages = false
ignore_bot_errors = true
```

# Sending messages

Simply send a stanza like this from your bot:

```xml
<message type="groupchat" to="channel@muc.example.com">
  <body>Beep boop, I'm a bot!</body>
  <nick xmlns="http://jabber.org/protocol/nick">Botty</nick>
</message>
```

## Use with mod_rest

Using [mod_rest] to interact with MUC suffers from the same need to join
with an online resource, so this module helps with that as well!

```bash
curl https://xmpp.example.com/rest/message/groupchat/room@muc.example.com \
    -d body="beep boop" \
    -d nick="Botty"
```

# Compatibility

Works with Prosody 0.12 or later.
