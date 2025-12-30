---
labels:
- 'Stage-Stable'
summary: Add a support contact to new registrations
...

Introduction
============

This Prosody plugin adds a default contact to newly registered accounts.

Usage
=====

Simply add "support\_contact" to your modules\_enabled list. When a new
account is created, the new roster would be initialized to include a
support contact.

Configuration
=============

  ------------------------- --------------------------------------------------------------------------------------------------------------------------------
  support\_contact          The bare JID of the support contact. The default is support@hostname, where hostname is the host the new user's account is on.
  support\_contact\_nick    Nickname of the support contact. The default is "Support".
  support\_contact\_group   The roster group in the support contact's roster in which to add the new user.
  ------------------------- --------------------------------------------------------------------------------------------------------------------------------

Compatibility
=============

  ------ -------
  0.10   Works
  0.9    Works
  0.8    Works
  0.7    Works
  0.6    Works
  ------ -------

**For 0.8 and older** use [version
999a4b3e699b](http://hg.prosody.im/prosody-modules/file/999a4b3e699b/mod_support_contact/mod_support_contact.lua).

Caveats/Todos/Bugs
==================

-   This only works for accounts created via in-band registration.
