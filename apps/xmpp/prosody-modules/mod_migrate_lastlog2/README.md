---
summary: mod_lastlog2 to mod_account_activity migrator
labels:
- Stage-Alpha
---


This is a migration script for converting data stored by [mod_lastlog2] (a
community module) to mod_account_activity (a newer module which is supplied
with Prosody 13.0 and later).

# Usage

This module performs the migration automatically as soon as it is loaded.

By default it will remove data from the mod_lastlog2 store unless you set
`migrate_lastlog2_auto_remove = false`.

# Compatibility

Works with Prosody 13.0 and later.
