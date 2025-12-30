---
labels:
- 'Stage-Alpha'
summary: Require visitors to accept something before being allowed in a room
...

# Introduction

This module sends a message to visitors of a room, prompting them to accept or reject it.

They get kicked if they reject it, and become members if they accept it.

# Setup

```lua
Component "rooms.example.org" "muc"
	modules_enabled = {
		"muc_require_tos";
	}
	tos_welcome_message = "Please read and accept the TOS of this service: https://lurk.org/TOS.txt"
	tos_yes_message = "Thanks, and welcome here!"
	tos_no_message = "Too bad."
```

Compatibility
=============

  ----- -----
  trunk Works
  ----- -----

