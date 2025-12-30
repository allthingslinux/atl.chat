---
summary: "Generate OMEMO debugging links"
labels:
- 'Stage-Alpha'
...

Introduction
============

This module allows you to view advanced information about OMEMO-encrypted messages,
and can be helpful to diagnose decryption problems.

It generates a link to itself and adds this link to the plaintext contents of
encrypted messages. This will be shown by clients that do not support OMEMO,
or are unable to decrypt the message.

This module depends on a working HTTP setup in Prosody, and honours the [usual
HTTP configuration options](https://prosody.im/doc/http).

Configuration
=============

There is no configuration for this module, just add it to
modules\_enabled as normal.

Compatibility
=============

  ----- -------
  0.11  Hopefully works
  trunk Works
  ----- -------
