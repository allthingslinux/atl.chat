Introduction
============

This module checks the IP addresses attempting to register an account
against a DNSBL, blocking the attempt if there is a hit.

Configuration
=============

  Option              Type     Default
  ------------------- -------- ------------
  registration\_rbl   string   *Required*

Compatibility
=============

Prosody Trunk
[1a0b76b07b7a](https://hg.prosody.im/trunk/rev/1a0b76b07b7a) or later.
