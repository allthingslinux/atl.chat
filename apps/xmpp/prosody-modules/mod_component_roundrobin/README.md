---
labels:
summary: 'Component round-robin load balancing module'
...

Introduction
============

This module enables multiple instances of external components to connect
at the same time, and does round-robin load-balancing of incoming
stanzas.

Example
=======

        Component "test.example.com"
            modules_enabled = { "component_roundrobin" }
            -- Other component options such as secrets here
