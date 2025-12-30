---
summary: Cache presence from remote users
...

Introduction
============

This module stores a timestamp of the latest presence received from
users contacts so that the client can see who is online faster when they
sign in, and won't have to wait for remote servers to reply.

Configuration
=============

Just enable the module.

    modules_enabled = {
        -- more modules
        "presence_cache";
    }

Advanced configuration
======================

The size of the cache is tuneable:

    presence_cache_size = 99

Compatibility
=============

Requires 0.10 or later
