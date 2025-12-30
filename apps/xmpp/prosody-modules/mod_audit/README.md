---
summary: Audit Logging
rockspec: {}
...

This module provides infrastructure for audit logging inside Prosody.

## What is audit logging?

Audit logs will contain security sensitive events, both for server-wide
incidents as well as user-specific.

This module, however, only provides the infrastructure for audit logging. It
does not, by itself, generate such logs. For that, other modules, such as
`mod_audit_auth` or `mod_audit_user_accounts` need to be loaded.

## A note on privacy

Audit logging is intended to ensure the security of a system. As such, its
contents are often at the same time highly sensitive (containing user names
and IP addresses, for instance) and allowed to be stored under common privacy
regulations.

Before using these modules, you may want to ensure that you are legally
allowed to store the data for the amount of time these modules will store it.
Note that it is currently not possible to store different event types with
different expiration times.

## Viewing the log

You can view the log using prosodyctl. This works even when Prosody is not
running.

For example, to view the full audit log for example.com:

```shell
prosodyctl mod_audit example.com
```

To view only host-wide events (those not attached to a specific user account),
use the `--global` option (or use `--no-global` to hide such events):

```shell
prosodyctl mod_audit --global example.com
```

To narrow results to a specific user, specify their JID:

```shell
prosodyctl mod_audit user@example.com
```

# Compatibilty

  Prosody-Version   Status
  ----------------- ---------------
  13.0              Works
  0.12              Does not work
