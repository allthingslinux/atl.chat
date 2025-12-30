# Introduction

This module allows you to make one or more MUCs as accessible to local users only.

# Details

Local users (anyone on the same server as the MUC) are granted automatic
membership when they first join the room. Users from other servers are
denied access (even if the room is otherwise configured to be open).

# Configuring

## Enabling

``` {.lua}
Component "rooms.example.net" "muc"
modules_enabled = {
    "muc_local_only";
}
```

## Settings

Specify a list of MUCs in your config like so:

```
muc_local_only = { "my-local-chat@conference.example.com" }
```

# Compatibility

Requires Prosody 0.11.0 or later.

# Future

It would be good to add a room configuration option.
