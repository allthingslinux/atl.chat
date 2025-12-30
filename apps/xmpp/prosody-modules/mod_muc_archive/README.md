---
labels:
- 'Stage-Beta'
summary: Log MUC messages to disk
...

# Introduction

This module logs the conversations of chatrooms running on the server to Prosody's data store.

This is a fork of [mod_muc_log](https://modules.prosody.im/mod_muc_log.html) which uses the newer storage API.
This allows you to also log messages to a SQL backend.

## Changes between mod_muc_archive and mod_muc_log:

- Use newer module storage API so that you can also store in SQL
- Adhere to config option `muc_log_all_rooms` (also used by mod_muc_mam)
- Add affiliation information in the logged stanza
- Remove code that set (and then removed) an "alreadyJoined" dummy element

NOTE: The changes are unlikely to be entirely backwards compatible because the stanza
being logged is no longer wrapped with `<stanza time=...>`.

Details
=======

mod\_muc\_archive must be loaded individually for the components that need it.

Assuming you have a MUC component already running on
conference.example.org then you can add muc\_archive to it like so:

    Component "conference.example.org" "muc"
       modules_enabled = {
          "muc_archive";
       }


Compatibility
=============

  ------ -----
  0.11   Works
  ------ -----
