---
labels:
- Stage-Beta
summary: Host status heartbeat
...

Introduction
============

This module integrates with [mod\_host\_status\_check] to provide heartbeats at regular intervals.

The only time you will generally want this, is if you are using [mod\_component\_client] to run Prosody as
an external component of another Prosody server that has [mod\_host\_status\_check] loaded and waiting for
heartbeats.

Alternatively you can run this on the same Prosody host as [mod\_http\_host\_status\_check] and it will simply
update a variable periodically to indicate that Prosody and timers are functional.

Configuration
=============

The following configuration options are supported:

```{.lua}
-- The number of seconds to wait between sending heartbeats
status_check_heartbeat_interval = 5

-- Set this to "remote" (the default) if you are using mod_component_client
-- and you want to send a heartbeat to a remote server. Otherwise
-- set it to "local" to send to mod_host_status_check on the same server.
status_check_heartbeat_mode = "remote"
```

Compatibility
=============

Works with Prosody 0.9.x and later.
