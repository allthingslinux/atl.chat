---
summary: Cache caps on user sessions
---

Description
===========

This module listens on presences containing caps (XEP-0115) and asks the client
for the corresponding disco#info if it changed.

It fires the c2s-capabilities-changed event once the disco#info result is
received.

Compatibility
=============

  ------- ---------------
  trunk   Works
  0.11    Does not work
  0.10    Does not work
  ------- ---------------
