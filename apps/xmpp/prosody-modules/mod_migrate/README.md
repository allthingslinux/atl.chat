---
summary: prosodyctl cross storage driver migration tool
...

Introduction
============

This module adds a command to `prosodyctl` for copying data between
storage drivers.

Usage
=====

    prosodyctl mod_migrate example.com <source-store>[-<store-type>] <target-driver> [users]*

`<source-store>` would be e.g. `accounts` or `private`. To migrate
archives, the optional suffix `<store-type>` would be set to `archive`,
so e.g. `archive2-archive` or `muc_log-archive`. Multiple stores can be
given if separated by commas.

`<target-driver>` is the storage driver to copy data to, sans the
`mod_storage_` prefix.

`mod_migrate` tries to request a list of users from `usermanager`, but
this does not always work. If so, you can supply usernames as arguments
after the target driver.

The process is something like this:

1.  Decide on the future configuration and add for example SQL
    connection details to your prosody config, but don't change the
    `store` option yet.
2.  With Prosody shut down, run
    `prosodyctl mod_migrate example.com accounts sql`
3.  Repeat for each store, substituting 'accounts'. E.g. vcards,
    private...
4.  Change the [`storage` configuration](https://prosody.im/doc/storage)
    to use the new driver.
5.  Start prosody again.

Examples
========

``` sh
prosodyctl mod_migrate example.com accounts,roster,private,vcard sql
```

Compatibility
=============

Should work with 0.8 and later.
