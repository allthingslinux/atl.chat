---
labels:
- 'Stage-Alpha'
summary: Personal account management command
...

Introduction
============

This module adds an ad-hoc command that lets an user change their
password. This is useful for clients that don't have support for
[XEP-0077](http://xmpp.org/extensions/xep-0077.html) style password
changing. In the future, it may provide other account management
commands.

Configuration
=============

    modules_enabled = {
        -- other modules --
        "adhoc_account_management",

    }

    close_sessions_on_password_change = true
    require_current_password = true
    require_confirm_password = true

  Option                                  Default   Description
  --------------------------------------- --------- ----------------------------------------------------------------
  close\_sessions\_on\_password\_change   true      Changing password invalidates other sessions the user may have
  require\_current\_password              true      Add a field for the current password
  require\_confirm\_password              true      Add a field for confirming the current password

Todo
====

Suggestions welcome,
