Description
===========

This module lists those users, who **have** used their account in a
defined time-frame, basically the inverse of [mod_list_inactive].

Dependencies
============

[mod_lastlog] must be enabled to collect the data used by this module.

Usage
=====

    prosodyctl mod_list_active example.com time [format]

Time is a number followed by 'day', 'week', 'month' or 'year'

Formats are:

  --------- ------------------------------------------------
  default   `user@example.com`
  event     `user@example.com last action`
  --------- ------------------------------------------------

Example
=======

    prosodyctl mod_list_active example.com 1year

Help
====

    prosodyctl mod_list_active
