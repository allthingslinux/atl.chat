---
labels:
- 'Stage-Beta'
- 'Type-Storage'
- ArchiveStorage
summary: XML file based archive storage
---

Introduction
============

This module implements stanza archives using files, similar to the
default "internal" storage. Unlike "internal", it saves messages in two
files per day (and per user), one containing metadata and one containing
the actual messages in XML format (hence the name).

Splitting data per day improves performance for larger archives as it
does not have to look through data from other days.

Configuration
=============

To use this with [mod\_mam] add this to your config:

``` lua
storage = {
    archive = "xmlarchive"
}
```

To use it with [mod\_mam\_muc] or [mod\_http\_muc\_log]:

``` lua
storage = {
    muc_log = "xmlarchive"
}
```

Refer to [Prosodys data storage documentation][doc:storage] for more
information.

Note that this module does not implement the "keyval" storage method and
can't be used by anything other than archives.


### Conversion to or from internal storage

This module stores data in a way that overlaps with the more recent
archive support in `mod_storage_internal`, meaning e.g. [mod_migrate]
will not be able to cleanly convert to or from the `xmlarchive` format.

To mitigate this, an migration command has been added to
`mod_storage_xmlarchive`:

``` bash
prosodyctl mod_storage_xmlarchive convert $DIR internal $STORE $JID+
```

Where `$DIR` is `to` or `from`, `$STORE` is e.g. `archive` or `archive2`
for MAM and `muc_log` for MUC logs. Finally, `$JID` is one or more JID
of the users or MUC rooms to be migrated.

To migrate all users/rooms on a particular host, pass a bare hostname.

::: {.alert .alert-danger}
Since this is a destructive command, don't forget to backup your data
first.

Prosody should *not* be running while converting data.
:::


Data structure
==============

Data is split in three kinds of files and messages are grouped by day.
Prosodys `util.datamanager` is used, so all special characters in these
filenames are escaped and reside under `hostname/store` in Prosodys Data
directory, commonly `/var/lib/prosody`.

`username.list`
:   A list of dates in `YYYY-MM-DD` format.

`username@YYYY-MM-DD.list`
:   Index containing metadata for messages stored on that day.

`username@YYYY-MM-DD.xml`
:   Messages in textual XML format, separated by newlines.

This makes it fairly simple and fast to find messages by timestamp.
Queries that are not time based, but limited to a specific contact may
be expensive as potentially the entire archive will be read.

Each archive ID is of the form `YYYY-MM-DD-random`, making lookups by
archive id just as simple as time based queries.

## Limitations

-   Only XML stanzas can be stored.
-   The deletion method only supports removing entire days at a time.

Compatibility
=============

  ------ ---------------
  trunk  Works
  0.12   Works
  ------ ---------------
