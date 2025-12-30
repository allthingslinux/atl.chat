---
labels:
- 'Stage-Alpha'
- 'Type-Web'
summary: Drop chatstates for specific domains.
rockspec:
  build:
    modules:
      mod_drop_chatstates: mod_drop_chatstates.lua
...

Introduction
============

This is a Prosody module to drop chatstates for specific domains.

Clients that request chatstates to virtual JIDs (i.e. those created by
modules like mod\_voipms to send/receive SMS/MMS on domains like
'sms.example.com') will, by design, receive errors indicating the
service is unavailable. While most clients will silently ignore this,
clients like profanity will not. This module allows us to drop responses
for chatstates on selected domains if we know they will never respond.

Configuration
=============

| option                    | type   | default | description
|---------------------------|--------|---------|-------------------------------|
| drop\_chatstates\_domains | table  | {}      | Domains to drop chatstates for

Sample module configuration:

```
modules_enabled = {
    "drop_chatstates";
}
drop_chatstates_domains = { "sms.example.com" }
```
