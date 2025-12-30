---
summary: Store token events in the audit log
rockspec:
  dependencies:
  - mod_audit
...

This module stores events relating to auth tokens, e.g. grant creations and revokations, in the audit log provided by `mod_audit`.
