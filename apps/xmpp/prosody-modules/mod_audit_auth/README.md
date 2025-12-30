---
summary: Store authentication events in the audit log
rockspec:
  dependencies:
  - mod_audit
...

This module stores authentication failures and authentication successes in the
audit log provided by `mod_audit`.

If mod_client_management is loaded, it will also record entries when a new
client is connected to the user's account for the first time. For non-SASL2
clients, this may have false positives.
