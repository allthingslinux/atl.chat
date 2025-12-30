---
labels:
- 'Stage-Alpha'
- 'Type-Storage'
summary: Experimental map store optimized for small incremental changes
...

This is an experimental storage driver where changed data is appended.
Data is simply written as `key = value` pairs to the end of the file.
This allows changes to individual keys to be written without needing to
write out the entire object again, but reads would grow gradually larger
as it still needs to read old overwritten keys. This may be suitable for
e.g. rosters where individual contacts are changed at a time. In theory,
this could also allow rolling back changes.

Requires 0.10
