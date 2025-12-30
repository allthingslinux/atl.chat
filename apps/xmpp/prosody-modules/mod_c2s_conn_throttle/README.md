---
labels:
- 'Stage-Stable'
summary: c2s connections throttling module
...

Introduction
============

This module allows to throttle those client connections which exceed a
n\*seconds limit.

Usage
=====

Copy the module folder into your prosody modules directory. Place the
module between your enabled modules either into the global or a vhost
section.

Optional configuration directives:

``` {.lua}

cthrottler_logins_count = 3 -- number of login attempts allowed, default is 3
cthrottler_time = 60 -- .. in number of seconds, default is 60
```

Info
====

-   0.8, works
-   0.9, works
