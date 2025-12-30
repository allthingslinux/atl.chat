---
labels:
- 'Stage-Beta'
summary: Record last timestamp of events
---

# Introduction

Similar to [mod_lastlog], this module records the last timestamp of
various events, but keeps the last timestamp per type of event, instead
of the last event.

# Usage

As with all modules, copy it to your plugins directory and then add it
to the modules\_enabled list:

``` {.lua}
modules_enabled = {
  -- other modules
  "lastlog2",
}
```

# Configuration

There are some options you can add to your config file:

  Name                   Type      Default   Description
  ---------------------- --------- --------- ---------------------------------
  lastlog\_ip\_address   boolean   false     Log the IP address of the user?

# Usage

You can check a user's last activity by running:

    prosodyctl mod_lastlog2 username@example.com

With Prosody trunk the command can be used via the shell:

    prosodyctl shell lastlog show username@example.com

# Compatibility

  Version   State
  --------- -------
  Any       *TBD*
