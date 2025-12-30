---
labels:
- 'Stage-Stable'
summary: 'Enforce a policy for OTR-encrypted messages'
...

Introduction
------------

[OTR, "Off The Record"](https://otr.cypherpunks.ca/), encryption allows
clients to encrypt messages such that the server cannot read/modify
them.

This module allows the server admin to require that all messages are
OTR-encrypted.

Configuration
-------------

Just enable the module by adding it to your global `modules_enabled`, or
if you only want to load it on a single host you can load it only for
one host like this:

    VirtualHost "example.com"
        modules_enabled = { "require_otr" }

#### Compatibility

  ------ -------
  0.10   Works
  0.9    Works
  0.8    Works
  ------ -------
