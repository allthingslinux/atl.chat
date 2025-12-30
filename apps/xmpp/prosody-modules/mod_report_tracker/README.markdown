---
labels:
- 'Stage-Alpha'
summary: 'Track abuse/spam reports from remote servers'
---

This module tracks reports received from remote servers about local user
accounts. The count of reports and the servers they came from is stored for
inspection by the admin or for use by other modules which might take action
against the reported accounts.

## Configuration

### Trusted reporters

You can configure which servers the module will trust reports from:

```
trusted_reporters = { "example.com", "example.net" }
```

Reports from non-domain JIDs are currently always ignored (even if listed).

Reports from domain JIDs which are not listed here are logged so the admin
can decide whether to add them to the configured list.

## Compatibility

Should work with 0.12, but has not been tested.

Tested with trunk (2024-11-22).

