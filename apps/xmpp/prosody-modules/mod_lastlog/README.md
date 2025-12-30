---
labels:
- 'Stage-Beta'
summary: Log last login time
...

Introduction
============

Simple module that stores the timestamp of when a user logs in.

Usage
=====

As with all modules, copy it to your plugins directory and then add it
to the modules\_enabled list:

``` lua
modules_enabled = {
  -- other modules
  "lastlog",
}
```

Configuration
=============

There are some options you can add to your config file:

  Name                      Type    Default Description
  ------------------------- ------- ------- ------------------------------------
  lastlog\_ip\_address      boolean false   Log the IP address of the user?
  lastlog\_stamp\_offline   boolean false   Add timestamp to offline presence?

Usage
=====

You can check a user's last activity by running:

    prosodyctl mod_lastlog username@example.com

Compatibility
=============

  ----- -------
  0.9   Works
  ----- -------
