---
labels:
- 'Stage-alpha'
summary: Save received chat markers into MUC archives'
...

Introduction
============

Chat markers (XEP-0333) specification states that markers _SHOULD_ be
archived.  This is already happening in one to one conversations in
the personal archives but not in Group Chats.  This module hooks the
_muc-message-is-historic_ event to customize the `mod_muc_mam`
behavior and have the chat markers archived.

Usage
=====

First copy the module to the prosody plugins directory.

Then add "muc\_mam\_markers" to your `modules\_enabled` list in your
MUC component's definition.

No configuration options are available.
