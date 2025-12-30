---
labels:
- 'Type-Storage'
- 'Stage-Alpha'
summary: Ejabberd SQL Read-only Storage Module
...

Introduction
============

This is a storage backend using Ejabberd’s SQL backend. It depends on
[LuaDBI][doc:depends#luadbi]

This module only works in read-only, and was made to be used by
[mod_migrate] to migrate from Ejabberd’s SQL backend.

Configuration
=============

Copy the module to the prosody modules/plugins directory.

In Prosody's configuration file, set:

    storage = "ejabberdsql_readonly"

EjabberdSQL options are the same as the [SQL
ones][doc:modules:mod_storage_sql#usage].

Compatibility
=============

  ------- ---------------------------
  trunk   Works
  0.10    Untested, but should work
  0.9     Does not work
  ------- ---------------------------
