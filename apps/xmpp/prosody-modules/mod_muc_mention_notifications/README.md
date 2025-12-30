# Configuring

This module lets Prosody notify users when they're mentioned in a MUC, even if they're not currently present in it.

Users need to be explicitly mentioned via XEP-0372 references.

In anonymous and semi-anonymous rooms, the mentioned user needs to have their nickname registered in the MUC so that Prosody can get the real JID from the referenced nickname.

NOTE: this module is not compatible with mod_block_strangers because the latter will block the notification messages from the MUC (since they're not "groupchat" messages).

## Enabling

``` {.lua}
Component "rooms.example.net" "muc"
modules_enabled = {
    "muc_mention_notifications";
}
```

## Settings

|Name |Description |Default |
|-----|------------|--------|
|muc_mmn_notify_unaffiliated_users| Notify mentioned users even if they are not members of the room they were mentioned in | false |
