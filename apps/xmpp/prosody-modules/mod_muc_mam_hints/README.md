---
labels:
- 'Stage-Alpha'
summary: 'Support XEP-0334: Message Processing Hints for MUC messages'
...

Introduction
============

This module will check for MUC messages with XEP-0334 Message
Processing Hints tags to qualify those messages as "historic"
for later MAM archiving or not.

Usage
=====

First copy the module to the prosody plugins directory.

Then add "muc\_mam\_hints" to your modules\_enabled list in your MUC
component:

``` {.lua}
Component "conference.example.org" "muc"
modules_enabled = {
  "muc_mam",
  "muc_mam_hints",
}
```
