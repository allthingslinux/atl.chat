---
summary: Throttle authentication attempts with optional tarpit
...

Introduction
============

This module lets you put a per-IP limit on the number of failed
authentication attempts.

It features an optioanal
[tarpit](https://en.wikipedia.org/wiki/Tarpit_%28networking%29), i.e.
waiting some time before returning an "authentication failed" response.

Configuration
=============

``` {.lua}
modules_enabled = {
  -- your other modules
  "limit_auth";
}

limit_auth_period = 30 -- over 30 seconds

limit_auth_max = 5 -- tolerate no more than 5 failed attempts

 -- Will only work with Prosody trunk:
limit_auth_tarpit_delay = 10 -- delay answer this long
```

Compatibility
=============

Requires 0.9 or later. The tarpit feature requires Prosody trunk.
