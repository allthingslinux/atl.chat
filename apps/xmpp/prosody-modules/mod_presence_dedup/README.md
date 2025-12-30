---
summary: Presence deduplication module
labels:
- 'Stage-Alpha'
...

This module tries to squash incoming identical presence stanzas to save
some bandwidth at the cost of increased memory use.

Configuration
=============

  Option                         Type     Default
  ------------------------------ -------- ---------
  presence\_dedup\_cache\_size   number   `100`

The only setting controls how many presence stanzas *per session* are
kept in memory for comparing with incoming presenece.

Requires Prosody 0.10 or later.
