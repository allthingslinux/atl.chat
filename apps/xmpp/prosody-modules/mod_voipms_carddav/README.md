---
labels:
- 'Stage-Alpha'
- 'Type-Web'
summary: Sync contacts from CardDAV in mod_voipms format.
rockspec:
  build:
    modules:
      mod_voipms_carddav: mod_voipms_carddav.lua
...

Introduction
============

This is a Prosody module to periodically sync virtual contacts via CardDAV to a roster. It handles the format for contacts produced by the mod_voipms module. It treats contacts with multiple numbers as distinct contacts with a type (e.g. cell, home, work). Further, for each DID, it will create a separate contact (and group) to denote the DID number it is associated with.

Note: Unlike the mod_voip.ms module, which you may run on a VirtualHost like "sms.example.com", this module should be enabled on the host that users login to. This is because it hooks the 'roster-load' function to inject virtual contacts, and these events will not be seen on subdomains. When building contact JIDs for each contact, it will use the module.host by default. If you are using "sms.example.com" for the mod_voip.ms module, you should set 'voipms_carddav_domain' to match.

Configuration
=============

| option                            | type   | default                | description
|-----------------------------------|--------|------------------------|------------|
| voipms\_carddav\_contact\_format  | string | [%alias] %name (%type) | Format to display contacts ([Work] John Smith (cell))
| voipms\_carddav\_domain           | string | module.host            | Domain part of JID
| voipms\_carddav\_jid\_map | table | table  | nil                    | JID->DIDs/CardDAV
| voipms\_carddav\_sync\_interval   | number | 86400                  | Interval (in seconds) to sync CardDAV
```
VirtualHost "example.com"
modules_enabled = {
    "voipms_carddav";
}
voipms_carddav_contact_format = "[%alias] %name (%type)"
voipms_carddav_domain = "sms.example.com"
voipms_carddav_jid_map = {
    ["john@example.com"] = {
        dids = {
            ["+10345678901"] = "Home",
            ["+10473828482"] = "Work",
        },
        carddav = {
            username = "john",
            password = "some_password",
            url = "https://cloud.example.com/remote.php/dav/addressbooks/users/john/contacts/"
        }
    },
    ["jane@example.com"] = {
        dids = {
            ["+10484828493"] = "Personal",
            ["+10483829293"] = "Professional",
        },
        carddav = {
            username = "john",
            password = "some_password",
            url = "https://cloud.example.com/remote.php/dav/addressbooks/users/john/contacts/"
        }
    }
}
voipms_carddav_sync_interval = 86400
```
