---
labels:
- Stage-Deprecated
summary: Privacy lists (XEP-0016) support
---

::: {.alert .alert-warning}
[XEP-0016 Privacy Lists] and this module has been deprecated, instead
use [mod_blocklist][doc:modules:mod_blocklist], included with Prosody.
:::

Introduction
------------

Privacy lists are a flexible method for blocking communications.

Originally known as mod\_privacy and bundled with Prosody, this module
was phased out in favour of the newer simpler blocking (XEP-0191)
protocol, implemented in [mod\_blocklist][doc:modules:mod_blocklist].

Configuration
-------------

None. Each user can specify their privacy lists using their client (if
it supports XEP-0016).

Compatibility
-------------

  ------ -------
  0.9    Works
  0.10   Works
  ------ -------
