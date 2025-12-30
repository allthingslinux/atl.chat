---
labels:
- 'Stage-Beta'
- 'Type-Auth'
summary: |
    Authentication module for 'HA1' hashed credentials in a text file, as
    used by reTurnServer
...

Introduction
============

This module authenticates users against hashed credentials stored in a
plain text file. The format is the same as that used by reTurnServer.

Configuration
=============

  Name              Default    Description
  ----------------- ---------- ---------------------------------
  auth\_ha1\_file   auth.txt   Path to the authentication file

Prosody reads the auth file at startup and on reload (e.g. SIGHUP).

File Format
===========

The file format is text, with one user per line. Each line is broken
into four fields separated by colons (':'):

    username:ha1:host:status

  Field      Description
  ---------- ----------------------------------------------------------------------------------
  username   The user's login name
  ha1        An MD5 hash of "username:host:password"
  host       The XMPP hostname
  status     The status of the account. Prosody expects this to be just the text "authorized"

More info can be found
[here](https://github.com/resiprocate/resiprocate/blob/master/reTurn/users.txt).

Example
-------

    john:2a236a1a68765361c64da3b502d4e71c:example.com:authorized
    mary:4ed7cf9cbe81e02dbfb814de6f84edf1:example.com:authorized
    charlie:83002e42eb4515ec0070489339f2114c:example.org:authorized

Constructing the hashes can be done manually using any MD5 utility, such
as md5sum. For example the user 'john' has the password 'hunter2', and
his hash can be calculated like this:

    echo -n "john:example.com:hunter2" | md5sum -

Compatibility
=============

  ------ -------
  0.9    Works
  0.10   Works
  ------ -------
