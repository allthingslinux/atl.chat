---
labels:
- 'Stage-Broken'
summary: 'Simple example of working component and HTTP polling.'
...

Introduction
============

Twitter has simple API to use, so I tried to deal with it via Prosody. I
didn't manage to finish this module, but it is nice example of component
that accepts registrations, unregistrations, does HTTP polling and so
on. Maybe someone will finnish this idea.

Details
=======

It does require some non-prosody Lua libraries: LuaJSON

Configuration
=============

At the moment no configuration needed, but you can configure some
variables inside code.

TODO
====

-   Send latest tweets to XMPP user
-   Reply user's messages to Twitter
-   OAuth support
-   User configuration (forms)
-   discuss about using cjson
-   [!!!!] rewrite to be compatible with 0.9+
-   drop? (since it is mod\_twitter in spectrum)

Compatibility
=============

  ------- ---------------------
  trunk   Currently Not Works
  0.9     Currently Not Works
  0.8     Works
  ------- ---------------------
