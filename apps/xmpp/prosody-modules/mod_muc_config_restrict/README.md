---
labels:
- 'Stage-Alpha'
summary: Restrict MUC configuration options to server admins
...

Introduction
============

Sometimes, especially on public services, you may want to allow people
to create their own rooms, but prevent some options from being modified
by normal users.

For example, using this module you can prevent users from making rooms
persistent, or making rooms publicly visible.

Details
=======

You need to supply a list of options that will be restricted to admins.
Available options can vary, but the following table lists Prosody's
built-in options (as defined in XEP-0045):

  Name                              Description
  --------------------------------- -------------------------------------------
  muc\#roomconfig\_roomname         The title/name of the room
  muc\#roomconfig\_roomdesc         The description of the room
  muc\#roomconfig\_persistentroom   Whether the room should remain when empty
  muc\#roomconfig\_publicroom       Whether the room is publicly visible
  muc\#roomconfig\_changesubject    Whether occupants can change the subject
  muc\#roomconfig\_whois            Control who can see occupant's real JIDs
  muc\#roomconfig\_roomsecret       The room password
  muc\#roomconfig\_moderatedroom    Whether the room is moderated
  muc\#roomconfig\_membersonly      Whether the room is members-only
  muc\#roomconfig\_historylength    The length of the room history

Some plugins may add other options to the room config (in Prosody
0.10+), for which you will need to consult their documentation for the
full option name.

Configuration
=============

Enable the plugin on a MUC host (do not put it in your global
modules\_enabled list):

``` {.lua}
Component "conference.example.com" "muc"
modules_enabled = { "muc_config_restrict" }
muc_config_restricted = {
  "muc#roomconfig_persistentroom"; -- Prevent non-admins from changing a room's persistence setting
  "muc#roomconfig_membersonly"; -- Prevent non-admins from changing whether rooms are members-only
}
```

Compatibility
=============

  ------- --------------
  trunk   Doesn't work (uses is_admin)
  0.12    Works?
  ------- --------------
