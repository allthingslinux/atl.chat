---
summary: Store user account lifecycle events in the audit log
rockspec:
  dependencies:
  - mod_audit
...

This module stores events related to user accounts in the audit log. Events
include:

- New user registered via IBR (user-registered)
- User deleted their account via IBR (user-deregistered)
- User requested deletion of their account (i.e. when a grace period is set) (user-deregistered-pending)
- User account disabled
- User account enabled

There are no configuration options for this module. It depends on mod_audit.
