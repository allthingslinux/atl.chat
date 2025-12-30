# Introduction

This module adds a room configuration option to hide inline media from MUCs and
display them as links instead.

This can be useful in public channels where content posted by users should not
be shown by default.

**Note:** You could consider the more useful [mod_muc_restrict_media] instead,
which allows affiliated users (e.g. members, admins, owners) to still send
inline media.

# Configuring

## Enabling

``` {.lua}
Component "rooms.example.net" "muc"
modules_enabled = {
    "muc_hide_media";
}
```

## Settings

A default setting can be provided in the config file:

``` {.lua}
muc_room_default_hide_media = true
```
