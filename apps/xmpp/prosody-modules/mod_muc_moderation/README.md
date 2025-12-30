---
labels:
- Stage-Beta
summary: Let moderators remove spam and abuse messages
---

# Introduction

This module implements [XEP-0425: Message Moderation].

# Usage

Moderation is done via a supporting client and requires a `moderator`
role in the channel / group chat.

# Configuration

Example [MUC component][doc:chatrooms] configuration:

``` {.lua}
Component "channels.example.com" "muc"
modules_enabled = {
    "muc_mam",
    "muc_moderation",
}
```

# Compatibility

  ------- ------------------------
  trunk   Works as of 2025-06-13
  13      Works
  0.12    Works
  ------- ------------------------

## XEP version

This module implements [XEP-0425] v0.2.1 (tombstones included) and v0.3.0
(except for tombstones).

## Clients

-   [Converse.js](https://conversejs.org/)
-   [Gajim](https://dev.gajim.org/gajim/gajim/-/issues/10107)
-   [clix](https://code.zash.se/clix/rev/6c1953fbe0fa)
-   [Cheogram](https://cheogram.com/)

### Feature requests

-   [Conversations](https://codeberg.org/iNPUTmice/Conversations/issues/20)
-   [Dino](https://github.com/dino/dino/issues/1133)
-   [Profanity](https://github.com/profanity-im/profanity/issues/1336)
