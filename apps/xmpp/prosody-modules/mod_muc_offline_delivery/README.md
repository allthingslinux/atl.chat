---
labels:
- 'Stage-Alpha'
summary: 'Support for sending MUC messages to offline users'
...

Introduction
============

This module implements support for sending messages in a MUC to affiliated users
who are not in the room. This is a custom extension by Tigase to allow push notifications
from MUCs to users who are not currently connected.

It is planned that this will evolve to a XEP in the near future.

The protocol is described below. It is implemented in the Siskin client for iOS.

Details
=======

Add to modules_enabled under your MUC component (i.e. **not** the global modules_enabled
list). There are no configuration options.

Compatibility
=============

Requires Prosody trunk (0.12) for the API introduced in commit 336cba957c88.

Protocol
========

To enable this feature, a client must fetch the registration form from a MUC,
as per XEP-0045. The form will include the usual field for nickname (this is
required), and also a boolean field named `{http://tigase.org/protocol/muc}offline`.

Submit the form with that field set to true, and the MUC will forward messages
to your bare JID when you are not connected to the room. Two things to note:

1. This will achieve nothing unless your server is capable of handling these
    messages correctly.
2. Messages are only sent when you are not in the room. This includes other
    resources of the same account.
