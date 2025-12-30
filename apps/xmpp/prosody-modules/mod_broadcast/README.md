---
labels:
- 'Stage-Stable'
summary: Broadcast a message to online users
...

Introduction
============

This module largely duplicates the functionality of the standard
mod\_announce that is included with Prosody. It was developed for
compatibility with some clients (e.g. iChat) that do not support ad-hoc
commands or sending to JIDs with the format
'example.com/announce/online'.

It may also be useful in other specific cases.

Configuration
=============

    Component "broadcast@example.com" "broadcast"

By default, only server admins are allowed to post to this address. You
can override this, by specifying the 'broadcast\_senders' option:

    Component "broadcast@example.com" "broadcast"
        broadcast_senders = { "user1@example.com", "user2@example.com" }

Compatibility
=============

  ------ -------
  0.9    Works
  0.10   Works
  trunk  Doesn't work (uses is_admin)
  ------ -------
