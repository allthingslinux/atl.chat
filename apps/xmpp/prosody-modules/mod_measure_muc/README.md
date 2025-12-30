---
labels:
- Statistics
summary: Collect statistics on Grout Chat
...

Description
===========

This module collects statistics from group chat component.

It collects current count of hidden, persistent, archive-enabled, password
protected rooms. The current count of room is also exposed (hidden+public).


Configuration
=============

mod\_measure\_muc must be load on MUC components (not globally):

```lua
Component "conference.example.com" "muc"
		modules_enabled = {
			"measure_muc";
		}
```

See also the documentation of Prosody’s [MUC module](https://prosody.im/doc/modules/mod_muc).

Compatibility
=============

  ------- -------------
  trunk   Works
  0.11    Works
  0.10    Unknown
  0.9     Does not work
  ------- -------------
