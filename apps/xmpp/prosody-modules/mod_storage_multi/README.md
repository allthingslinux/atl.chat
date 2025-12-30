---
summary: Multi-backend storage module (WIP)
labels:
- NeedDocs
- Stage-Alpha
...

Introduction
============

This module attemtps to provide a storage driver that is really multiple
storage drivers. This could be used for storage error tolerance or
caching of data in a faster storage driver.

Configuration
=============

An example:

``` {.lua}
storage = "multi"
storage_multi_policy = "all"
storage_multi = {
    "memory",
    "internal",
    "sql"
}
```

Here data would be first read from or written to [mod\_storage\_memory],
then internal storage, then SQL storage. For reads, the first successful
read will be used. For writes, it depends on the `storage_multi_policy`
option. If set to `"all"`, then all storage backends must report success
for the write to be considered successful. Other options are `"one"` and
`"majority"`.
