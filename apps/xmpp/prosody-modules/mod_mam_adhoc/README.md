---
labels:
- 'Stage-Alpha'
summary: 'Ad-hoc interface to Message Archive Management Settings'
...

Introduction
============

This module complements mod\_mam by allowing clients to change archiving
preferences through an Ad-hoc command.

Details
=======

When enabled, an "Archive Settings" command should appear in the list of
Ad-hoc commands available. This allows the user to change default policy
(always, never, roster) and which JIDs to always store or never store.

Usage
=====

First copy the module to the prosody plugins directory.

Then add "mam\_adhoc" to your modules\_enabled list:

``` {.lua}
modules_enabled = {
  -- ...
    "mam",
  "mam_adhoc",
  -- ...
}
```
