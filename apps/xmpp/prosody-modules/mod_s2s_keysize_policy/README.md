---
summary: Distrust servers with too small keys
...

Introduction
============

This module sets the security status of s2s connections to invalid if
their key is too small and their certificate was issued after 2014, per
CA/B Forum guidelines.

Details
=======

Certificate Authorities were no longer allowed to issue certificates
with public keys smaller than 2048 bits (for RSA) after December 31
2013. This module was written to enforce this, as there were some CAs
that were slow to comply. As of 2015, it might not be very relevant
anymore, but still useful for anyone who wants to increase their
security levels.

When a server is determined to have a "too small" key, this module sets
its chain and identity status to "invalid", so Prosody will treat it as
a self-signed certificate istead.

"Too small"
-----------

The definition of "too small" is based on the key type and is taken from
[RFC 4492].

  Type     bits
  ------ ------
  RSA      2048
  DSA      2048
  DH       2048
  EC        233

Compatibility
=============

Works with Prosody 0.9 and later. Requires LuaSec with [support for
inspecting public keys](https://github.com/brunoos/luasec/pull/19).
