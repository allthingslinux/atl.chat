---
labels:
- 'Type-Storage'
- 'Stage-Alpha'
summary: MongoDB Storage Module
...

Introduction
============

This is a storage backend that uses MongoDB. Depends on [luamongo
bindings](https://github.com/mwild1/luamongo)

This module is not under active development and has a number of issues
related to limitations in MongoDB. It is not suitable for production
use.

Configuration
=============

Copy the module to the prosody modules/plugins directory.

In Prosody's configuration file, set:

    storage = "mongodb"

MongoDB options are:

  Name         Description
  ------------ -------------------------------------------------------------------
  server       hostname:port
  username     your username for the given database
  password     your password for the given database (either raw or pre-digested)
  is\_digest   whether the password field has been pre-digested

Compatibility
=============

  ------- ---------------------------
  trunk   Untested, but should work
  ------- ---------------------------
