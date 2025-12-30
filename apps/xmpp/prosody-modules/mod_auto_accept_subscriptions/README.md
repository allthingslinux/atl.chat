---
labels:
- 'Stage-Beta'
summary: Automatically accept incoming subscription requests on behalf of users
...

Introduction
============

In some environments where all users on the system have mutual trust in
each other, it's sometimes fine to skip the usual authorization process
to add someone to your contact list and see their status.

This module sets Prosody to automatically accept incoming subscription
authorization requests, and add the contact to the user's contact list,
without intervention from the user.

Configuration
=============

Simply add the module to your modules\_enabled list like any other
module:

        modules_enabled = {
            ...
            "auto_accept_subscriptions";
            ...
        }

This module has no further configuration.

Compatibility
=============

  Prosody-Version Status
  --------------- -----------
  0.12            Should work
  0.11            Should work
  0.10            Works
