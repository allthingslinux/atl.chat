---
rockspec:
  dependencies:
  - mod_track_muc_joins
summary: Limit rate of outgoing unsolicited messages
---

Introduction
============

This module limits the rate of outgoing unsolicited messages from local
clients. Optionally, unsolicited messages coming in from remote servers
may be limited per s2s conneciton. A message counts as "unsolicited" if
the receiving user hasn't added the sending user to their roster.

The module depends on [mod\_track\_muc\_joins] in order to allow sent
messages to joined MUC rooms.

Configuration
=============

To set a limit on messages from local sessions:

``` {.lua}
unsolicited_messages_per_minute = 10
```

To enable limits on unsolicited messages from s2s connections:

``` {.lua}
unsolicited_s2s_messages_per_minute = 100
```
