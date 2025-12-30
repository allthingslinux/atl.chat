---
labels:
- 'Stage-Beta'
summary: 'Log/archive all user messages'
...

Introduction
============

Often service administrators need to log their users' messages for
reasons such as auditing and compliance. This module simply logs user
messages to simple text files, which can be easily searched, archived or
removed on a regular basis.

Usage
=====

Simply load the module and it will start logging. Reloading Prosody
(e.g. with a SIGHUP) will cause it to close any open logs (and re-open
them if necessary).

Configuration
=============

  Option name             Description
  ----------------------- -----------------------------------------------------------------------------------------------------------------------
  message\_logging\_dir   The directory to save message logs in. Default is to create a 'message\_logs' subdirectory inside the data directory.

Compatibility
=============

  ----- -------
  0.9   Works
  ----- -------
