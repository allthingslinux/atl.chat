---
summary: "XEP-0283: Moved"
labels:
- 'Stage-Alpha'
...

Introduction
============

This module implements [XEP-0283: Moved](http://xmpp.org/extensions/xep-0283.html),
a way for contacts to notify you that they have moved to a new address.

This module is not necessary to generate such notifications - that can be done
by clients, for example. What this module does is automatically verify such
notifications and, if verification is successful, automatically update your
roster (contact list).

Configuration
=============

There is no configuration for this module, just add it to `modules_enabled` as normal.

Compatibility
=============

  Prosody-Version Status
  --------------- -----------
  trunk           Should Work
  0.12            Works
