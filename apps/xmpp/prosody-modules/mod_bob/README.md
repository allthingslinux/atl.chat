---
summary: Cache Bits of Binary on MUC services
rockspec:
  dependencies:
    - mod_cache_c2s_caps
---

Description
===========

This module extracts cid: URIs (as defined in XEP-0231) from messages, and
replies with their content whenever another client asks for the actual data.

Usage
=====

```lua
Component "rooms.example.org" "muc"
	modules_enabled = {
		"bob";
		...
	}
```
