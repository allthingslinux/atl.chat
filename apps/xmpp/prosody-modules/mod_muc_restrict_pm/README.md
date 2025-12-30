---
labels:
- 'Stage-Obsolete'
summary: Limit who may send and recieve MUC PMs
...

::: {.alert .alert-warning}
This feature has been merged into
[mod_muc][doc:modules:mod_muc] in trunk and is therefore obsolete when used with a version >0.12.x or trunk.
It can still be used with Prosody 0.12.
:::

# Introduction

This module adds configurable MUC options that restrict and limit who may send MUC PMs to other users.

If a user does not have permissions to send a MUC PM, the MUC will send a policy violation stanza.

# Setup

```lua
Component "conference.example.org" "muc"

modules_enabled = {
	"muc_restrict_pm";
}
```

Compatibility
=============

  version   note
  --------- ---------------------------------------------------------------------------
  trunk     [Integrated](https://hg.prosody.im/trunk/rev/47e1df2d0a37) into `mod_muc`
  0.12      Works
