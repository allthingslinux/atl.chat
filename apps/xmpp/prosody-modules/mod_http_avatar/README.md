---
summary: Serve avatars from HTTP
...

Introduction
============

This module serves avatars from local users who have one set in their
vCard, see XEP-0054 and XEP-0153.

Configuring
===========

Simply load the module.  Avatars are then available at
http://<host>:5280/avatar/<username>

    modules_enabled = {
        ...
        "http_avatar";
    }

Compatibility
=============

  ------- --------------
  trunk   Works
  0.11    Works
  0.10    Should work
  ------- --------------
