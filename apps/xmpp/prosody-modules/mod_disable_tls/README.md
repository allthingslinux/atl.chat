---
labels:
- 'Stage-Beta'
summary: Disable TLS on certain client ports
...

Introduction
============

This module can be used to prevent Prosody from offering TLS on client
ports that you specify. This can be useful to work around buggy clients
when transport security is not required.

Configuration
=============

Load the module, and set `disable_tls_ports` to a list of ports:

        disable_tls_ports = { 5322 }

Don't forget to add any extra ports to c2s\_ports, so that Prosody is
actually listening for connections!

Compatibility
=============

  ----- -------
  0.9   Works
  ----- -------
