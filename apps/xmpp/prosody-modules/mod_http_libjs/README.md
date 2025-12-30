---
labels:
- 'Stage-Stable'
summary: 'Serve common Javascript libraries'
...

Introduction
============

This module serves common static CSS and Javascript libraries from the
filesystem, allowing other HTTP modules to easily reference them.

The default configuration works out of the box with Debian (and derivatives)
`libjs-*` packages, such as `libjs-jquery` and `libjs-bootstrap`.

You can override the filesystem location using the `libjs_path` configuration
option. The default is `/usr/share/javascript`.

Compatibility
=============

  Prosody-Version Status
  --------------- --------------------
  trunk           Works as of 24-12-08
  0.12            Works
