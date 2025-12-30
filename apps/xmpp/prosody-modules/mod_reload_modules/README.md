---
labels:
- 'Stage-Stable'
summary: Automatically reload modules with the config
...

Introduction
------------

By default Prosody does not reload modules at runtime unless instructed
to via one of its admin interfaces. However sometimes you want to easily
reload a module to apply new settings when the config changes.

mod\_reload\_modules will reload a set list of modules every time
Prosody reloads its config (e.g. on SIGHUP).

Configuration
-------------

Add "reload\_modules" to modules\_enabled. Then the list of modules to
reload using the 'reload\_modules' option in your config like so:

    reload_modules = { "groups", "tls" }

This would reload mod\_groups and mod\_tls whenever the config is
reloaded. Note that on many systems this will be at least daily, due to
logrotate.

Compatibility
-------------

  ----- -------
  0.9   Works
  ----- -------
