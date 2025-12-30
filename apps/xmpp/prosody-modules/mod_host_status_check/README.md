---
labels:
- Stage-Beta
summary: Host status check
...

Introduction
============

This module allows you to monitor the state of hosts and components in your Prosody server. For example,
it will track whether components are connected and (if the component supports it) listen for heartbeats
sent by the component to indicate that it is functioning.

This module does not expose any interface to access the status information itself. See [mod\_http\_host\_status\_check]
for a module that allows you to access host status information over HTTP(S).

Configuration
=============

There are no configuration options for this module.

You should enable it on every host that you want to monitor, by adding it to modules\_enabled. Note
that to monitor components, adding to the global modules\_enabled list will not suffice - you will
need to add it to the component's own modules\_enabled, like this:

``` {.lua}
Component "mycomponent.example.com"
   modules_enabled = { "host_status_check" }
```

Compatibility
=============

Works with Prosody 0.9.x and later.
