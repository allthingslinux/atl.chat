---
labels:
- 'Type-Storage'
- 'Stage-Alpha'
summary: Metronome Read-only Storage Module
...

Introduction
============

This is a storage backend using Metronome Lua storage.

This module only works in read-only, and was made to be used by [mod\_migrate]
to migrate from Metronome’s storage.

So far it has only been tested migrating to sqlite, because
mod\_storage\_internal relies on the same `data_path` variable as this module,
and thus would overwrite the files we just read.

I’ve also only tested it on a dump from a Metronome configured by Yunohost, so
using LDAP and such for user accounts, I don’t yet know how to migrate from
different Metronome account storages.

Configuration
=============

Copy the module to the prosody modules/plugins directory.

In Prosody's configuration file, set:

    storage = "metronome_readonly"
    data_path = "/var/lib/metronome"

To run the actual migration, run these two commands (replace `<host>` with the domain you want to migrate):

    prosodyctl mod_migrate <host> roster,vcard,private,cloud_notify,pep,pep_data-archive,offline-archive,archive-archive,uploads-archive sql
    prosodyctl mod_migrate muc.<host> config,persistent,vcard_muc,muc_log-archive sql

It will create a file in `/var/lib/metronome/prosody.sqlite`, after which you
can change your configuration file to point to it, or alternatively you can
perform a second migration to the internal storage if you prefer that.

Compatibility
=============

  ------------------------ --------
  trunk (as of 2025-01-10) Works
  0.12                     Untested
  ------------------------ --------
