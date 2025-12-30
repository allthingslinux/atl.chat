---
labels:
- 'Stage-Beta'
summary: Automatically populate vcard based on account details
...

Introduction
============

It is possible for the user to supply more than just a username and
password when creating an account using
[mod\_register](https://prosody.im/doc/modules/mod_register). This
module automatically copies over that data to the user's vcard.

Details
=======

There is no configuration for this module, just add it to
modules\_enabled as normal.

Note that running this on a public-facing server that prompts for email
during registration will make the user's email address publicly visible
in their vcard.

Compatibility
=============

  ----- -------
  0.9   Works
  ----- -------
