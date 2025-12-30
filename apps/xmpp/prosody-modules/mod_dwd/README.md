---
summary: 'Dialback-without-Dialback'
...

Introduction
============

This module implements an optimization of the Dialback protocol, by
skipping the dialback step for servers presenting a valid certificate.

Configuration
=============

Simply add the module to the `modules_enabled` list.

        modules_enabled = {
            ...
            "dwd";
        }

Compatibility
=============

  ------------------ --------------------------
  0.10               Built into mod\_dialback
  0.9 + LuaSec 0.5   Works
  0.8                Doesn't work
  ------------------ --------------------------
