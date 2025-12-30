---
summary: Collect statistics on rate of log messages
...

Introduction
============

If you ever wanted to collect statistics on the number of log messages,
this is the module for you!

Setup
=====

After [installing the module](https://prosody.im/doc/installing_modules)
and adding it to modules\_enabled as most other modules, you also need
to add it to your logging config:

``` {.lua}
log = {
  -- your other log sinks
  info = "/var/log/prosody/prosody.log"
  -- add this:
  { to = "measure" };
}
```

Then log messages will be counted by
[statsmanager](https://prosody.im/doc/developers/core/statsmanager).

Compatibility
=============

Reqires Prosody 0.10 or above.
