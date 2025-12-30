---
labels:
- 'Stage-Alpha'
- 'Type-Auth'
summary: PAM authentication module
---

Introduction
============

This module makes Prosody authenticate users against PAM (Linux
Pluggable Authentication Modules)

Dependencies
============

The module depends on [lua-pam](https://github.com/devurandom/lua-pam)
and [LuaPosix](https://github.com/luaposix/luaposix).

Setup
=====

Create a `/etc/pam.d/xmpp` with something like this:

    auth    [success=1 default=ignore]  pam_unix.so obscure sha512 nodelay
    auth    requisite           pam_deny.so
    auth    required            pam_permit.so

And switch authentication provider in the Prosody config:

    authentication = "pam"

Compatibility
=============

Compatible with 0.9 and up
