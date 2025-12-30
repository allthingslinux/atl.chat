---
labels:
- 'Stage-Stable'
summary: Log warning when event handlers take too long
...

Introduction
============

Most activities in Prosody take place within our built-in events framework, for
example stanza processing and HTTP request handling, authentication, etc.

Modules are able to execute code when an event occurs, and they should return
as quickly as possible. Poor performance (e.g. slow or laggy server) can be caused
by event handlers that are slow to respond.

This module is able to monitor how long each event takes to be processed, and
logs a warning if an event takes above a certain amount of time, including
providing any details about the event such as the user or stanza that triggered it.

The aim is to help debug why a server may not be as responsive as it should be,
and ultimately which module is to blame for that.

Configuration
======================

There is a single configuration option:

```
   -- Set the number of seconds an event may take before
   -- logging a warning (fractional values are ok)
   log_slow_events_threshold = 0.5
```

Metrics
=======

In addition to the log messages, a new 'slow_events' metric will be exported to
your configured stats backend (if any).

Compatibility
-------------

  ------- --------------
  trunk   Works
  0.10    Works
  0.9     Doesn't work
  0.8     Doesn't work
  ------- --------------
