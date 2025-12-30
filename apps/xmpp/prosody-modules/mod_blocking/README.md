---
labels:
- Stage-Deprecated
rockspec:
  dependencies:
  - mod_privacy_lists
summary: "XEP-0191: Simple Communications Blocking support"
---

::: {.alert .alert-warning}
This module is deprecated as it depends on the deprecated
[mod_privacy_lists], use the core module
[mod_blocklist][doc:modules:mod_blocklist] instead.
:::

Introduction
============

Privacy lists are a widely implemented protocol for instructing your
server on blocking communications with selected users and services.

However experience has shown that the power and flexibility of the
rule-based system that privacy lists allow is very often much more
complex than the user needs, and that in most cases a simple block on
all communications to or from a list of specified JIDs would suffice.

Such a protocol would also allow much simpler user interface design than
the current attempts at full privacy list interfaces.

Details
=======

Simple Communications Blocking was developed to solve the above issues,
and allows the client to manage a simple list of blocked JIDs. This
plugin implements support for that protocol in Prosody, however the
actual blocking is still managed by mod\_privacy, so it is **required**
for that plugin to be loaded (this may change in future).

An XEP-0191 implementation without dependency on mod\_privacy is
available in Prosody 0.10 as [mod\_blocklist][doc:modules:mod_blocklist].

Configuration
=============

Simply ensure that [mod_privacy_lists] and mod_blocking are loaded in
your modules_enabled list:

        modules_enabled = {
                        -- ...
                        "privacy_lists",
                        "blocking",
                        -- ...

Compatibility
=============

  ------ ---------------------------------------------
  0.10   Works but will conflict with mod\_blocklist
  0.9    Works
  0.8    Works
  0.7    Works
  0.6    Doesn't work
  ------ ---------------------------------------------
