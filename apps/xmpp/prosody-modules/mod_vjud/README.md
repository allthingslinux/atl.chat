---
labels:
- 'Stage-Alpha'
summary: 'XEP-0055: Jabber Search'
...

Introduction
============

Basic implementation of [XEP-0055: Jabber Search].

Details
=======

This module has two modes. One mode requires users to opt-in to be
searchable, then allows users to search the list of those users. The
second mode allows search across all users.

Usage
=====

First copy the module to the prosody plugins directory.

Then add "vjud" to your modules\_enabled list:

        modules_enabled = {
                        -- ...
                        "vjud",
                        -- ...
            }

Alternatively, you can load it as a component:

        Component "search.example.com" "vjud"

(Some old clients require this)

Configuration
=============

  Option       Default    Description
  ------------ ---------- --------------------------------
  vjud\_mode   "opt-in"   Choose how users are listed in the directory ("opt-in" or "all")

Compatibility
=============

  ------- ---------------------------------
  0.8     Works, but only the opt-in mode
  0.9     Works
  trunk   Works
  ------- ---------------------------------

Note that the version for 0.8 and 0.9 are slightly different.
