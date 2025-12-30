---
labels:
- 'Stage-Alpha'
summary: 'Implement XEP-0328: JID Prep for clients'
...

Introduction
============

This is a plugin that implements the JID prep protocol defined in
<https://xmpp.org/extensions/xep-0328.html>

Details
=======

JID prep requests can happen over XMPP using the protocol defined in the
document linked above, or alternatively over HTTP. Simply request:

    http://server:5280/jid_prep/USER@HOST

The result will be the stringprepped JID, or a 400 Bad Request if the
given JID is invalid.

Compatibility
=============

  ----- -------
  0.9   Works
  ----- -------
