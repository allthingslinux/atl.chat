---
summary: Ad-hoc commands for managing MUC hats
---

# Introduction

This module provides an internal API (i.e. to other modules) to manage
'hats' for users in MUC rooms.

Hats (first defined in [XEP-0317], currently deferred) are additional identifiers
that can be attached to users in a group chat. For example in an educational
context, you may have a 'Teacher' hat that allows students to identify their
teachers.

Hats consist of a machine-readable unique identifier (a URI), and optionally
a human-readable label.

This module provides ad-hoc commands for MUC service admins to add/remove hats
to/from users in MUC rooms. It depends (automatically) on mod_muc_hats_api.

## Configuration

```
Component "conference.example.com" "muc"
  modules_enabled = { "muc_hats_adhoc" }
```

## Usage

To successfully use the module you will need to use an XMPP client that is
capable of sending commands to a specific host (e.g. via the service discovery
browser in Gajim, Psi/Psi+ and other clients), and you'll find the commands
on the MUC host.

Also note that the display of hats in clients is currently non-existent, but
will hopefully improve after [XEP-0317] is resurrected or replaced.

