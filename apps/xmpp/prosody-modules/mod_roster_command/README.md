---
labels:
- 'Stage-Beta'
summary: Manage rosters through prosodyctl
...

Introduction
------------

This module allows you to perform various actions on user rosters via
prosodyctl.

Details
-------

After putting this module in your modules directory you can use it via
prosodyctl like this:

    prosodyctl mod_roster_command COMMAND [OPTIONS...]

**Note:** Do not add mod\_roster\_command to your Prosody config file.
This is unnecessary because it will automatically be loaded by
prosodyctl when you use it.

### Commands

    subscribe user@host contact@host

Subscribes the user to the contact's presence. That is, the user will
see when the contact is online (but the contact won't see the user).

    subscribe_both user@host contact@host

The same as the 'subscribe' command, but performs the subscription in
both directions, so that both the contact and user will always see each
other online.

    unsubscribe user@host contact@host

Removes a subscription to the contact's presence.

    unsubscribe_both user@host contact@host

Same as unsubscribe, but also revokes a contact's subscription to the
user's presence.

    rename user@host contact@host [name] [group]

Sets or updates a name for a contact in the user's roster, and moves the
contact to the given group, if specified.

Compatibility
-------------

  ----- -------
  0.9   Works
  0.8   Works
  ----- -------
