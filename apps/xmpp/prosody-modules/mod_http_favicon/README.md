---
summary: HTTP favicon
...

Introduction
============

This simple module serves a `favicon.ico` from prosodys HTTP server and
nothing else.

Configuring
===========

Simply load the module. The icon can be replaced by adding a `favicon`
option to the config.

    modules_enabled = {
        ...
        "favicon";
    }

    favicon = "/path/to/my-favicon.ico" -- Override the built in one

Compatibility
=============

  ------- --------------
  trunk   Works
  0.9     Works
  0.8     Doesn't work
  ------- --------------
