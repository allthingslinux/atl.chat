---
labels:
- 'Stage-Alpha'
summary: 'Device identification'
...

Description
============

This is an experimental module that aims to identify the different
devices (technically clients) that a user uses with their account.

It is expected that at some point this will be backed by a nicer protocol,
but it currently uses a variety of hacky methods to track devices between
sessions.

Usage
=====

``` {.lua}
modules_enabled = {
    -- ...
    "devices",
    -- ...
}
```

Configuration
=============

Option summary
--------------

  option                         type                    default
  ------------------------------ ----------------------- -----------
  max\_user\_devices             number                  `5`


Compatibility
=============

  ------- -----------------------
  trunk   Works
  0.11    Works
  0.10    Does not work
  ------- -----------------------
