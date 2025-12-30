---
labels:
- 'Stage-Alpha'
summary: 'Require MUC occupant nicknames to no match some patterns'
---

Introduction
============

This checks the nickname of a joining user against a configurable list of
[Lua patterns](https://www.lua.org/manual/5.2/manual.html#6.4.1), and prevents
them from joining if it matches any of them.

Configuration
=============

There is a single configuration option, `muc_reserve_nick_patterns` and the
default is `{}` - i.e. allow everything.

Compatibility
=============

Requires Prosody 0.11 or higher.
