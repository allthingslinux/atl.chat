---
labels:
- 'Stage-Beta'
summary: 'Automatically activate/deactivate hosts on reload'
...

Introduction
============

By default Prosody does not automatically activate/deactivate hosts when
they are added to and removed from the configuration.

This module will activate/deactivate hosts as necessary when the
configuration is reloaded.

This module was sponsored by [Exa Networks](http://exa-networks.co.uk/).

Configuration
=============

Add the module to your **global** modules\_enabled list:

        modules_enabled = {
            ...
            "auto_activate_hosts";
            ...
        }

There are no configuration options for this module.

Compatibility
=============

  ----- -------
  0.9   Works
  ----- -------
