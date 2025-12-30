---
summary: Block s2s connections based on admin blocklist
labels:
- 'Stage-Beta'
...

This module uses the blocklists set by admins for blocking s2s
connections.

So if an admin blocks a bare domain using [Blocking Command][xep191]
via [mod\_blocklist][doc:modules:mod_blocklist] then no s2s connections
will be allowed to or from that domain.

# Configuring

The role or roles that determine whether a
particular users blocklist is used can be configured:

```lua
-- This is the default:
admin_blocklist_roles = { "prosody:operator", "prosody:admin" }
```

# Compatibility

  Prosody Version   Status
  ----------------- ------------------------
  trunk             Works as of 2025-06-13
  13.0              Works
  0.12              Works
