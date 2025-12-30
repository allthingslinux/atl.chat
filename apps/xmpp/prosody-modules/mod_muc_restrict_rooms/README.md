---
summary: Regexp based room restriction module
...

Introduction
============

This module allows disabling room creation based on regexp patterns
defined in configuration.

Dependencies
============

This module depends on **muc/rooms** module. If **muc/rooms** is not
loaded, this module won't work.

How to load the module
======================

Copy the module to the prosody modules/plugins directory.

In Prosody's configuration file, under the desired MUC component
definition, add:

      modules_enabled = {
        ...
        "mod_muc_restrict_rooms";
        ...
      }

**Note**: This module *shouldn't* be loaded in the global
**modules\_enabled**, otherwise it won't work.

Configuration
=============

**mod\_muc\_restrict\_rooms** has several variables which let you
configure the patterns for room names you want to ban, establish
exceptions for those patterns and even deciding whether admins can or
not bypass the prohibition.

  Name                           Description                                                                                                                                                                                                                                                                                                                                                                                                                           Example                                                                                                       Default value
  ------------------------------ ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- ------------------------------------------------------------------------------------------------------------- ---------------
  muc\_restrict\_matching        Table in the key/value format (keys for patterns and values for reasons) that determines which rooms shouldn't be created. The key is a regexp and must be specified between quotation marks (see example). Room names will be evaluated always lowercase, so define your patterns taking this into consideration. Users that try to join any room that matches one of those rules will get an error telling them they cannot join.   muc\_restrict\_matching = { ["\^admin"] = "Rooms that start with 'admin' are reserved for staff use only" }   {}
  muc\_restrict\_exceptions      String format table that contains exceptions to the above defined rules. Room names specified here will bypass the muc\_restrict\_matching restrictions and will be available for anyone                                                                                                                                                                                                                                              muc\_restrict\_exceptions = { "admins\_are\_good", "admins\_rocks" }                                          {}
  muc\_restrict\_allow\_admins   Boolean that determines whether users in the **admin** table are able to bypass any room restriction. If ser to *true*, they will be able to bypass those rules.                                                                                                                                                                                                                                                                      muc\_restrict\_allow\_admins = true                                                                           false

Compatibility
=============

  ----- -------------
  trunk Doesn't work (uses is_admin)
  0.9   Works
  0.8   Should work
  ----- -------------
