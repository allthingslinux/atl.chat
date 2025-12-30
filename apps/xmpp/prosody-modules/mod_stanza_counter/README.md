---
labels:
- 'Stage-Stable'
summary: Simple incoming and outgoing stanza counter
...

Introduction
============

This module counts incoming and outgoing stanzas from when the instance
started, and makes the data available to other modules by creating a
global prosody. object

Details
=======

The counter module is "stanza\_counter", the example output module is
stanza\_counter\_http.

Usage
=====

Copy both files into prosody's module directory and place 'em into your
enabled modules (stanza\_counter\_http requires to be loaded into the
global section!)

Config for stanza\_counter\_http:

``` {.lua}

stanza_counter_basepath = "/counter-path-custom/"
```

Info
====

-   As of now to count components stanzas, it needs to be manually
    loaded (inserted into modules\_enabled of the components' sections)
    on these.
-   This version isn't compatible with previous versions of prosody
    (looks at 0.8-diverge branch for olders).
