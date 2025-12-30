---
summary: Serve PEP avatars from HTTP
---

# Introduction

This module serves avatars from local users who have published
[XEP-0084: User Avatar] via [PEP][doc:modules:mod_pep].

# Configuring

Simply load the module. Avatars are then available at
`http://<host>:5280/pep_avatar/<username>`

    modules_enabled = {
        ...
        "http_pep_avatar";
    }

# Access

Users must [configure] their Avatar PEP nodes to be public, otherwise
access is denied.

# Compatibility

  ------- ---------------
  trunk   Works
  0.11    Works
  0.10    Does not work
  ------- ---------------

[configure]: https://xmpp.org/extensions/xep-0060.html#owner-configure
