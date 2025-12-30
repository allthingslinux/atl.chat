---
summary: Log server status changes to audit log
rockspec: {}
...

This module records server status (start, stop, crash) to the audit log
maintained by [mod_audit].

## Configuration

There is a single option, `audit_status_heartbeat_interval` which specifies
the interval at which the "server is running" heartbeat should be updated (it
is stored in Prosody's configured storage backend).

To detect crashes, Prosody periodically updates this value at the specified
interval. A low value will update more frequently, which causes additional I/O
for Prosody. A high value will give less accurate timestamps for "server
crashed" events in the audit log.

The default value is 60 (seconds).

```lua
audit_status_heartbeat_interval = 60
```

## Compatibility

This module requires Prosody trunk (as of April 2023). It is not compatible
with 0.12.
