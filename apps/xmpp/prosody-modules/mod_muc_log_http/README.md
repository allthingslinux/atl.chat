---
labels:
- 'Stage-Obsolete'
summary: Provides a web interface to stored chatroom logs
...

::: {.alert .alert-danger}
This module depends on an obsolete module for storing data in an inefficient format.

For a modern approach, see [mod_http_muc_log] which relies on [mod_muc_mam][doc:modules:mod_muc_mam].
:::

Introduction
============

This module provides a built-in web interface to view chatroom logs
stored by [mod\_muc\_log](mod_muc_log.html).

Installation
============

Just copy the folder muc\_log\_http as it is, into the modules folder of
your Prosody installation.

Configuration Details
=====================

Example configuration:

        Component "conference.example.com" "muc"
        modules_enabled = {
            .....
            "muc_log";
            "muc_log_http";
            .....
        }

        muc_log_http = { -- These are the defaults
            show_join = true;
            show_presences = true;
            show_status = true;
            theme = "prosody";
            url_base = "muc_log";
        }

**show\_join** sets the default for showing joins or leaves.
**show\_status** sets the default for showing status changes.

The web interface would then be reachable at the address:

    http://conference.example.com:5280/muc_log/

TODO
====

-   Log bans correctly
-   Quota \~ per day ?!
-   Testing testing :)
