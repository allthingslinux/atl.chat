---
labels:
- 'Stage-Alpha'
summary: API to notify server admins
---

# Introduction

This module provides an API for other module developers to send
notification messages to host admins.

# Configuration

None required.

# Developers

Example:

```
local notify_admins = module:depends("admin_notify").notify;

notify("This is an important message for you, admins")
```

# Compatibility

Prosody trunk or later. Incompatible with 0.11 or lower.
