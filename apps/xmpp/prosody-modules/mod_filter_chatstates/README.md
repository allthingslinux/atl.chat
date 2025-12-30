---
summary: Drop chat states from messages to inactive sessions
...

::: {.alert .alert-info}
This module discards certain kinds of stanzas that are unnecessary to deliver to inactive clients. This is technically against the XMPP specification, and has the potential to cause bugs. However it is being used by some people successfully, and reduces the overall bandwidth usage for mobile devices.
On the other hand it does not save battery usage in a relevant way compared to other `csi` modules.
Consider using [mod_csi_simple][doc:modules:mod_csi_simple] that is incuded in prosody since Version 0.11.
:::

Introduction
============

Some mobile XMPP client developers consider [Chat State
Notifications](http://xmpp.org/extensions/xep-0085.html) to be a waste
of power and bandwidth, especially when the user is not actively looking
at their device. This module will filter them out while the session is
considered inactive. It depends on [mod\_csi](/mod_csi.html) for
deciding when to begin and end filtering.

Configuration
=============

There is no configuration for this module, just add it to
modules\_enabled as normal.

Compatibility
=============

  ----- -------
  0.11   Works
  0.10   Works
  ----- -------
