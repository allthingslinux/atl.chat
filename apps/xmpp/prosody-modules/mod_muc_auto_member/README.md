---
labels:
- 'Stage-Beta'
summary: "Automatically register new MUC participants as members"
...

# Introduction

This module automatically makes anybody who joins a MUC become a registered
member. This can be useful for certain use cases.

Note: there is no automatic cleanup of members. If you enable this on a server
with busy public channels, your member list will perpetually increase in size.

Also, there is currently no per-room option for this behaviour. That may be
added in the future, along with membership expiry.

# Configuration

There is currently no configuration for this module. The module should be
enabled on your MUC component, i.e. in the modules_enabled option under your
Component:

``` {.lua}
Component "conference.example.com" "muc"
    modules_enabled = {
        "muc_auto_member";
    }
```

# Compatibility

0.12 and later.
