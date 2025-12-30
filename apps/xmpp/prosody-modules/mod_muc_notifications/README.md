---
labels:
- 'Stage-alpha'
summary: 'Notify of MUC messages to not present members'
...

Introduction
============

This module listens to MUC messages and sends a notification to the
MUC members not present in the MUC at that moment.

By default, the notification will be a message with a simple text as body.

By sending this "out-of-MUC" notification, not-joined members will be able to
know that new messages are available.

Usage
=====

First copy the module to the prosody plugins directory.

Then add "muc\_notifications" to your modules\_enabled list in your
MUC component:

```{.lua}
Component "conference.example.org" "muc"
modules_enabled = {
	"muc_notifications",
}
```

You may also want to enable "offline\_hints" module so the notification messages
sent by this module are not added to the offline storage for later delivery.

Configuration
=============

  Option                      Description
  --------------------------- ----------------------------------------------------------------------------------------------
  muc\_notification\_invite   If set to `true`, the notification sent will take the form of a MUC invite. (default: `false`)
