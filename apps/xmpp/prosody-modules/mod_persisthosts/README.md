Introduction
============

This module creates stub configuration files for newly activated hosts.

Configuration
=============

A single option exists, `persisthosts_path`, which is the path where new
stub configuration files are created. It defaults to `"conf.d"`, and is
treated as relative to the configuration directiory [^1] unless set to
an absolute path.

[^1]: usually `/etc/prosody` on \*nix systems
