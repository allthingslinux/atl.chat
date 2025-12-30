---
labels:
- 'Stage-Alpha'
summary: 'Support for encrypted payloads in push notifications'
...

Introduction
============

This module implements support for a [Encrypted Push Notifications](https://xeps.tigase.net//docs/push-notifications/encrypt/),
a custom extension to [XEP-0357: Push Notifications](https://xmpp.org/extensions/xep-0357.html).

It is planned that this will evolve to a XEP in the near future.

Details
=======

Add to `modules_enabled`, there are no configuration options.

When used with Prosody 0.12.x, it has an extra dependency on
[luaossl](http://25thandclement.com/~william/projects/luaossl.html)
which is available in Debian as
[`lua-luaossl`](https://tracker.debian.org/pkg/lua-luaossl) or via
`luarocks install luaossl`.

Prosody 13.0.x and trunk does not require this.

# Compatibility

  Prosody Version   Status
  ----------------- -----------------------------------
  13.0.x            Works
  0.12.x            Works (with `luaossl`, see above)
