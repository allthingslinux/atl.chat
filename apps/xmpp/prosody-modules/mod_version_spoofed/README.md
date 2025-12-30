---
summary: Server version spoofer
...

This module is a fork of the built-in mod_version that adds spoofing options. Please do not use this module to mess with services that provide statistics and information. Instead, contact the hosts of such services and request blacklisting.

# Configuration

  Name                   Description                                           Type      Default value
  ---------------------- --------------------------------------------------- -------- ---------------
  server\_name           the reported name of the server software            string   "Prosody"
  server\_version        the reported version of the server software         string   `prosody.version`
  server\_platform       the reported platform of the server software        string   nil

This replaces mod_version, so you must disable mod_version when enabling or the modules might conflict. Unconfigured, this module acts the same as mod_version.

As a tip if you want complete spoofing, you should use the `name` option under your VirtualHost and components to hide mentions of Prosody.

Compatibility
=============

  version   note
  --------- ---------------------------------------------------------------------------
  13        Should work
  0.12      Works
