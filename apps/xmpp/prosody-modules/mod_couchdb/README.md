---
labels:
- 'Stage-Alpha'
- 'Type-Storage'
summary: A CouchDB backend for Prosody
...

***Note:** This module needs updating to the 0.8 storage module API.*

Introduction
============

This is an experimental Prosody backend for CouchDB.

Configuration
=============

In your config file, under the relevant host, add:

    datastore = "couchdb";
    couchdb_url = "http://127.0.0.1:5984/database-name";

Compatibility
=============

This module was developed as a prototype during development of the
storage provider API in Prosody 0.8. The final storage provider API is
different, so this module needs updates to work.

Quirks
======

This implementation is a work in progress.

-   The data stored in couchdb is limited to: account data, rosters,
    private XML and vCards
