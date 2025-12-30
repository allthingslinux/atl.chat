---
labels:
- 'Stage-Alpha'
summary: Discard offline stanzas instead of generating stanza errors if mod_offline is not loaded
...

Introduction
============

By default without mod_offline stanzas that would go to offline storage
trigger error stanzas sent back to the sender to inform him of undeliverable stanzas.

But if you use MAM on your server and are certain, all of your clients are using it,
you can use this module to disable the error stanzas.
If mod_offline is loaded, this module will do nothing.

Warning
=======

You most certainly *should not* use this module if you cannot be certain
that *all* your clients support and use MAM!

Compatibility
=============

  ----- -------------------------------------------------------------------
  trunk Works
  0.10  Works
  0.9   Untested but should work
  ----- -------------------------------------------------------------------
