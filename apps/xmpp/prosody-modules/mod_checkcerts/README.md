---
labels:
- Stage-Broken
summary: Certificate expiry reminder
...

::: {.alert .alert-info} 
This module is incompatible with prosody since version 0.10.
:::

Introduction
============

This module periodically checks your certificate to see if it is about
to expire soon. The time before expiry is printed in the logs. About a
week before a certificate expires, reminder messages will be sent to
admins.

Configuration
=============

Simply add the module to the `modules_enabled` list. You can optionally
configure how long before expiry to start sending messages to admins.

    modules_enabled = {
        ...
        "checkcerts"
    }
    checkcerts_notify = 7 -- ( in days )

Compatibility
=============

Needs LuaSec 0.5+

Originally written for Prosody 0.9.x, apparently incompatible with
0.10 or greater
