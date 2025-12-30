# Introduction

This module implements [XEP-xxxx: Room Activity Indicators](https://xmpp.org/extensions/inbox/room-activity-indicators.html).

## Requirements

This module currently depends on mod_muc_markers, so review the requirements for that module.

# Configuring

## Enabling

``` {.lua}
Component "rooms.example.net" "muc"
modules_enabled = {
    "muc_rai";
    "muc_markers";
    "muc_mam";
}
```

## Settings

|Name |Description |Default |
|-----|------------|--------|
|muc_rai_max_subscribers| Maximum number of active subscriptions allowed | 1024 |

# Compatibility

Requires Prosody trunk (2020-04-15+).