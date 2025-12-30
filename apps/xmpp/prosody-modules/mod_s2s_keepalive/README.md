---
labels:
- 'Stage-Beta'
summary: Keepalive s2s connections
...

Introduction
============

This module periodically sends [XEP-0199] ping requests to remote servers to keep your connection alive.

Configuration
=============

Simply add the module to the `modules_enabled` list like any other module. 
By default, all current s2s connections will be pinged
periodically. To ping only a subset of servers, list these in `keepalive_servers`.
The ping interval can be set using `keepalive_interval`.

If no response to the ping has been received in about 10 minutes (or `keepalive_timeout` seconds) the s2s connections are closed.

``` lua
modules_enabled = {
    ...
    "s2s_keepalive"
}

keepalive_servers = { "conference.prosody.im"; "rooms.swift.im" }
keepalive_interval = 90 -- (in seconds, default is 60 )
keepalive_timeout = 300 -- (in seconds, default is 593 )
```

Compatibility
=============

  Prosody Version   Status
  ----------------- ------------------------
  trunk             Works as of 2025-06-13
  13.0              Works
  0.12              Works
