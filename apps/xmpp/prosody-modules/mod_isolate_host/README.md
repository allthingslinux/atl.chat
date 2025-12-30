---
labels:
- 'Stage-Beta'
summary: Prevent communication between hosts
...

Introduction
============

In some environments it is desirable to isolate one or more hosts, and
prevent communication with external, or even other internal domains.

Loading mod\_isolate\_host on a host will prevent all communication with
JIDs outside of the current domain, though it is possible to configure
exceptions.

**Note:** if you just want to prevent communication with external
domains, this is possible without a plugin. See [Prosody: Disabling
s2s](http://prosody.im/doc/s2s#disabling) for more information.

This module was sponsored by [Exa Networks](http://exa-networks.co.uk/).

Configuration
=============

To isolate all hosts by default, add the module to your global
modules\_enabled:

``` {.lua}
modules_enabled = {
  ...
    "isolate_host";
  ...
}
```

Alternatively you can isolate a single host by putting a
modules\_enabled line under the VirtualHost directive:

``` {.lua}
VirtualHost "example.com"
modules_enabled = { "isolate_host" }
```

After enabling the module, you can add further options to add exceptions
for the isolation:

  Option                     Description
  -------------------------- -----------------------------------------------------------------------------------------
  isolate\_except\_domains   A list of domains to allow communication with.
  isolate\_except\_users     A list of user JIDs allowed to bypass the isolation and communicate with other domains.

**Note:** Admins of hosts are always allowed to communicate with other
domains

Compatibility
=============

  ----- -------
  0.9   Works
  ----- -------
