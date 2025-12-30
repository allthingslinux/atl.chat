---
summary: 'Block outgoing stanzas from users'
...

Introduction
============

This module blocks all outgoing stanzas from a list of users.

Using
=====

Add mod_block_outgoing to the enabled modules in your config file:
``` {.lua}
modules_enabled = {
	-- ...
		"block_outgoing",
	-- ...
}
```

Either in a section for a certain host or the global section define which users and what stanzas to block:
``` {.lua}
block_outgoing_users = { "romeo@example.com", "juliet@example.com" }
block_outgoing_stanzas = { "message", "iq", "presence" }
```

block_outgoing_stanzas defaults to "message" if not specified.

Compatibility
=============

  ------- --------------
  trunk   Doesn't work (uses is_admin)
  0.12    Works
  0.11    Works
  ------- --------------

