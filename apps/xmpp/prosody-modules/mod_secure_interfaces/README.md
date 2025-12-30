---
labels:
- 'Stage-Beta'
summary: 'Mark some network interfaces (e.g. loopback/LAN) as always secure'
...

Introduction
============

Sometimes you might run clients without encryption on the same machine
or LAN as Prosody - and you want Prosody to treat them as secure (e.g.
allowing plaintext authentication) even though they are not encrypted.

This module allows you to tell Prosody which of the current server's
interfaces (IP addresses) that you consider to be on secure networks.

Configuration
=============

Configuration is simple, just load the module like any other by adding
it to your modules\_enabled list:

        modules_enabled = {
            ...
            "secure_interfaces";
            ...
        }

Then set the list of secure interfaces (just make sure it is set in the
global section of your config file, and **not** under a VirtualHost or
Component):

        secure_interfaces = { "127.0.0.1", "::1", "192.168.1.54" }

Compatibility
=============

  ------- ---------
  0.9     Works
  0.8     Unknown
  trunk   Works
  ------- ---------
