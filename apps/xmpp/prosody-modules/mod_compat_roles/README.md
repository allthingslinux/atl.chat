---
labels:
- Stage-Alpha
summary: Compatibility layer for Prosody's future roles API
---

Introduction
============

This module provides compatibility with Prosody's new role and permissions
system. It aims to run on Prosody 0.11 and 0.12, providing a limited version
of the new API backed by is_admin() (which is not going to be present in trunk
and future Prosody versions).

It is designed for use by modules which want to be compatible with Prosody
versions with and without the new permissions API.

Configuration
=============

There is no configuration.

Usage (for developers)
======================

If you are a module developer, and want your module to work with Prosody trunk
and future releases, you should avoid the `usermanager.is_admin()` function.

Instead, depend on this module:

```
module:depends("compat_roles")
```

Then use `module:may()` instead:

```
if module:may(":do-something") then
  -- Blah
end
```

For more information on the new role/permissions API, check Prosody's
developer documentation at https://prosody.im/doc/developers/permissions

Compatibility
=============

Requires Prosody 0.11 or 0.12.
