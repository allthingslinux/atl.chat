---
labels:
summary: 'Module enabling "on-hold" functionality'
...

Introduction
============

Enable mod\_onhold to allow temporarily placing messages from particular
JIDs "on hold" -- i.e. store them, but do not deliver them until the
hold status is taken away.

Details
=======

Right now, it is configured through adding JIDs to a list in
prosody.cfg.lua. Eventually, more dynamically configurable support will
be added (i.e. with ad-hoc commands or some such thing).

Simply enable mod\_onhold in your list of modules, and then add a line:

onhold\_jids = { "someone@address.com", "someoneelse@address2.com" }

Until those JIDs are removed, messages from those JIDs will not be
delivered. Once they are removed and prosody is restarted, they will be
delivered the next time the user to which they are directed logs on.
