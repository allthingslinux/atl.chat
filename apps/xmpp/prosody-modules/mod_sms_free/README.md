---
labels:
- 'Stage-Alpha'
summary: XMPP to SMS gateway using the HTTP API provided by mobile.free.fr
...

Introduction
============

This module sends an SMS to your phone when you receive a message on XMPP when
your status is xa or disconnected.

Note that it doesn’t support sending SMS to anyone else than yourself, in that
it is quite different from other gateways.

Configuration
=============

In prosody.cfg.lua:

    modules_enabled = {
        "sms_free",
    }

Usage
=====

Every user who wants to use this gateway can issue an ad-hoc command to their
server, then follow the instructions and start receiving messages by SMS when
they are unavailable or xa.

Compatibility
=============

  ----- ------------------------------------
  trunk Works
  0.11  Does not work (SNI support required)
  ----- ------------------------------------
