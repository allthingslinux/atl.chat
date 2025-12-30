---
summary: 'XEP-0502 (MUC Activity Indicator) implementation'
...

This module provides an implementation of [XEP-0502 (MUC Activity Indicator)](https://xmpp.org/extensions/xep-0502.html) for Prosody.

To enable it, load it on a MUC host, for example:

```lua
Component "chat.domain.example" "muc"
    modules_enabled = { "muc_activity" }
```

When this module is loaded, it will expose the average number of messages per hour for all public MUCs.
The number is calculated over a 24 hour window.

Note that this module may impact server performance on servers with many MUCs.
