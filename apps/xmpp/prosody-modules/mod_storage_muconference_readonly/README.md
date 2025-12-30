---
labels:
- 'Type-Storage'
- 'Stage-Alpha'
summary: MU-Conference SQL Read-only Storage Module
...

Introduction
============

This is a storage backend using MU-Conference’s SQL storage. It depends
on [LuaDBI][doc:depends#luadbi]

This module only works in read-only, and was made to be used by
[mod_migrate] to migrate from MU-Conference’s SQL storage.

You may need to convert your 'rooms' and 'rooms\_lists' tables to
utf8mb4 before running that script, in order not to end up with
mojibake.  Note that MySQL doesn’t support having more than
191 characters in the jid field in this case, so you may have to change
the table schema as well.

Configuration
=============

Copy the module to the prosody modules/plugins directory.

In Prosody's configuration file, set:

    storage = "muconference_readonly"

MUConferenceSQL options are the same as the [SQL
ones][doc:modules:mod_storage_sql#usage].

Compatibility
=============

  ------- ---------------------------
  trunk   Works
  0.10    Untested, but should work
  0.9     Does not work
  ------- ---------------------------
