---
labels:
- 'Stage-Alpha'
summary: 'XEP-077 IBR registration URL redirect'
---

Introduction
============

Registration redirect to out of band URL as described in  [XEP-0077: In-Band Registration](http://xmpp.org/extensions/xep-0077.html#redirect).

Details
=======

The already existing module `mod_register_redirect` doesn’t add a stream feature advertising its capabilities  and thus doesn’t work with clients like Conversations.

This module tries to take a simpler and more straight forward approach for admins who just want to redirect to an URL and do not need the features provided by `mod_register_redirect`.

Usage
=====

Set `allow_registration` to `false` and point `register_oob_url` to the URL that handles your registration.

Compatibility
=============

  ----- -----------------------------------------------------------------------------
  0.10  Works
  ----- -----------------------------------------------------------------------------
