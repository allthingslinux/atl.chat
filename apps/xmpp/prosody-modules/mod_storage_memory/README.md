---
labels:
- 'Stage-Merged'
- 'Type-Storage'
- ArchiveStorage
summary: 'Simple memory-only storage module'
...


::: {.alert .alert-warning}
This module has been merged into
[prosodys storage backend as "memory"][doc:storage] and is therefore obsolete.
You will be redirected shortly.
:::

Introduction
============

This module acts as a normal storage module for Prosody, but saves all
data in memory only. All data is lost when the server stops. This makes
it useful for testing, or certain specialized applications.

Details
=======

Because the accounts store will always begin empty, it is mostly useful
combined with an authentication plugin which doesn't use Prosody's
storage API, or with [mod\_auth\_any](mod_auth_any.html), or you can
create user accounts manually each time the server starts.

Compatibility
=============

  ----- -------
  0.9   Works
  ----- -------
