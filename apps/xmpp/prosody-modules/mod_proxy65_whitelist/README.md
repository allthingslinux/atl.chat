---
labels:
- Stage-Alpha
summary: Limit which file transfer users can use
...

Introduction
------------

This module attempts to restrict use of non-whitelisted XEP-0065
proxies.

Configuration
-------------

Without any options, the module will restrict users to local [proxy65
components](https://prosody.im/doc/modules/mod_proxy65).

    -- additional proxies to allow
    allowed_streamhosts = { "proxy.eu.jabber.org" }

The module will add all local proxies to that list. To prevent it from
doing that, set

    allow_local_streamhosts = false
