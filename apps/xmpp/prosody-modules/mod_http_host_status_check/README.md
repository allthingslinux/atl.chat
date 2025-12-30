---
labels:
- Stage-Beta
summary: HTTP Host Status Check
...

Introduction
============

This module exposes serves over HTTP the information collected by [mod\_host\_status\_check] and
[mod\_host\_status\_heartbeat] in a convenient format for automated monitoring tools.

Configuration
=============

[mod\_http\_status\_check] relies on Prosodys HTTP server and mod\_http for
serving HTTP requests. See [Prosodys HTTP server
documentation][doc:http] for information about how to
configure ports, HTTP Host names etc.

Simply add this module to modules\_enabled for the host you would like to serve it from.

There is a single configuration option:

``` {.lua}
    -- The maximum number of seconds that a host can go without sending a heartbeat,
    -- before we mark it as TIMEOUT (default: 5)
    status_check_heartbeat_threshold = 5;
```

Compatibility
=============

Works with Prosody 0.9.x and later.
