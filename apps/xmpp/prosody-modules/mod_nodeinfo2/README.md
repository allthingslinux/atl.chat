---
labels:
- Stage-Alpha
---

Introduction
============

This module exposes a [nodeinfo2](https://git.feneas.org/jaywink/nodeinfo2)
.well-known URL for use e.g. from
[the-federation.info](https://the-federation.info).

Configuration
=============

Enable the `nodeinfo` module in your global `modules_enabled` section:
```
modules_enabled = {
    ...
    "nodeinfo2"
    ...
}
```

Set the `nodeinfo2_expose_users` option to false if you don’t want to expose
statistics about the amount of users you host:
```
nodeinfo2_expose_users = false
```

Set the `nodeinfo2_expose_posts` option to false if you don’t want to expose
statistics about the amount of messages being exchanged by your users:
```
nodeinfo2_expose_posts = false
```

This module depends on
[mod\_lastlog](https://modules.prosody.im/mod_lastlog.html) to calculate user
activity, and [mod\_http](https://prosody.im/doc/http). Most of its
configuration actually happens in this dependency.

Compatibility
=============

  ------- --------------------
  trunk   Does not work [^1]
  0.11    Should work
  ------- --------------------

[^1]: not after
    [5f15ab7c6ae5](https://hg.prosody.im/trunk/rev/5f15ab7c6ae5)
