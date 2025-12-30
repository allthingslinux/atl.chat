---
labels:
- 'Stage-Alpha'
summary: 'HTTP-based account data import/export using XEP-0227'
...

Introduction
============

This module allows a user to import or export account data using a simple
HTTP API. The data is expected to be in the format described by [XEP-0227:
Portable Import/Export Format for XMPP-IM Servers](https://xmpp.org/extensions/xep-0227.html).

Note that this module does not provide any UI for direct interaction from
users - it is expected that any UI will be provided elsewhere. For example,
this module is used by the [Snikket web portal](https://github.com/snikket-im/snikket-web-portal/).

For Developers
==========

TBD.

Compatibility
=============

Requires Prosody trunk (270047afa6af).
