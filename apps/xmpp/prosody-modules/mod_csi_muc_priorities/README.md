# Introduction

This module lets users specify which of the group chats they are in are
more or less important. This influences when
[mod_csi_simple][doc:modules:mod_csi_simple] decides to send
stanzas vs waiting until there is more to send. Users in many large
public channels might benefit from this.

# Configuration

The module is configured via ad-hoc an command called *Configure group
chat priorities* that should appear in the menus of compatible clients.

The command presents a form that accepts a list of XMPP addresses.
Currently you can specify channels as lower priority (which is suitable
for e.g. noisy public channels) or higher priority (which is suitable
for e.g. small private channels where immediate message delivery is
desired).  You can also specify whether mucs default to lower priority
or not.

A message of type groupchat from an address in the low priority list will
not be considered important enough to send it to an inactive client,
unless it is from the current user or mentions of their nickname.
**Note** that mention support require the separate module
[mod_track_muc_joins] to also be loaded.

``` {.lua}
modules_enabled = {
    -- other modules etc

    "csi_simple",
    "csi_muc_priorities",
    "track_muc_joins", -- optional
}
```
