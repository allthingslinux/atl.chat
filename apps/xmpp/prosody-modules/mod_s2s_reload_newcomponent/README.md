---
labels:
summary: |
    Module to automatically load new components when config:reload is done
    in console
...

Introduction
============

Currently, module:reload command in console doesn't load new components.
This module will automatically load the new components (if any) when the
config:reload command is run in the console.

Details
=======

In order to use the plugin, simply load the plugin by adding
"s2s\_reload\_newcomponent" to the modules enabled list. The plugin
requires configuration to be reloaded via console plugin's
config:reload() command.

Now, add a new component in the prosody configuration and then run
config:reload() command in the console plugin. The new component should
become active in prosody at this point and can be used.

Dependency
==========

Needs console plugin to reload configuration.

Compatibility
=============

  ----- -------
  0.7   works
  ----- -------
