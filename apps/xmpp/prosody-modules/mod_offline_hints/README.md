---
labels:
- 'Stage-alpha'
summary: Do not store in offline storage messages hinted with no-store'
...

Introduction
============

`mod_offline` does not take into account XEP-334 tags.  This module
will not add to the offline storage those messages tagged with
`<no-store />`.

Usage
=====

First copy the module to the prosody plugins directory.

Then add "offline\_hints" to your modules\_enabled list in your
configuration.

No configuration options are available.
