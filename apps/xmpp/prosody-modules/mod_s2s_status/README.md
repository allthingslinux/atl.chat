---
labels:
- 'Stage-Alpha'
summary: 'Track the status and health of s2s connections'
...

Introduction
============

Prosody already gives some insight into current s2s connections, e.g. via
the `s2s:show()` command in the console. This will tell you about all current
s2s connections.

However sometimes this is not enough. For example if an s2s connection fails
to establish, it won't show up - you have to go digging through the log file
looking for the errors instead.

This module maintains a record of recent connection attempts to a remote
domain. You can use this module to answer questions such as:

- Why did the last connection attempt to `example.com` fail?
- When did I last have a successful connection with `example.com`?
- Are my s2s connections generally stable?

**Note:** At the time of writing, this module is not yet finished, and should
be considered a proof-of-concept.

# Configuration

Just load the module as normal:

``` {.lua}
modules_enabled = {
  ...
  "s2s_status";
  ...
}
```

# Compatibility

trunk (0.12) and later, e.g. due to [60676b607b6d](https://hg.prosody.im/trunk/rev/60676b607b6d).
