---
labels:
- 'Type-Auth'
- 'Stage-Stable'
summary: SQL Database authentication module
...

Introduction
============

Allow client authentication to be handled by an SQL database query.

Unlike mod\_storage\_sql (which is supplied with Prosody) this module
allows for custom schemas (though currently it is required to edit the
source).

Configuration
=============

As with all auth modules, there is no need to add this to
modules\_enabled. Simply add in the global section, or for the relevant
hosts:

        authentication = "sql"

This module reuses the database configuration of
[mod\_storage\_sql](http://prosody.im/doc/modules/mod_storage_sql) (the
'sql' option), which you can set even if you are not using SQL as
Prosody's primary storage backend.

The query is currently hardcoded in the module, so you will need to edit
the module to change it. The default query is compatible with jabberd2
DB schema.

Compatibility
=============

  ----- -------
  0.8   Works
  ----- -------
