# Introduction

This module adds a room configuration option to hide inline media from
unaffiliated users in MUCs and display them as links instead.

This can be useful in public channels where content posted by users should not
be shown by default.

# Configuring

## Enabling

``` {.lua}
Component "rooms.example.net" "muc"
modules_enabled = {
    "muc_restrict_media";
}
```

## Settings

A default setting can be provided in the config file:

``` {.lua}
muc_room_default_restrict_media = true
```
