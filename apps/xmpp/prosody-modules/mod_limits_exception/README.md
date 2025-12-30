---
labels:
- Stage-Obsolete
summary: Allow specified JIDs to bypass rate limits
---

This module allows you to configure a list of JIDs that should be allowed to
bypass rate limit restrictions.

It is designed for Prosody 0.11.x. Prosody 0.12.x supports this feature
natively.

## Configuration

First, enable this module by adding `"limits_exception"` to your
`modules_enabled` list.

Next, configure a list of JIDs to exclude from rate limiting:

```
unlimited_jids = { "user1@example.com", "user2@example.net" }
```

## Compatibility

Made for Prosody 0.11.x only.

Using this module with Prosody trunk/0.12 may cause unexpected behaviour.
