---
labels:
- Stage-Alpha
summary: Unified Push provider
---

This module implements a [Unified Push](https://unifiedpush.org/) Provider
that uses XMPP to talk to a Push Distributor (e.g. [Conversations](http://codeberg.org/iNPUTmice/Conversations)).

It allows push notifications to be delivered to apps on your device over XMPP.
This means notifications can be delivered quickly and efficiently (apps don't
need to repeatedly poll for new notifications).

For a list of compatible apps, see the [UnifiedPush apps list](https://unifiedpush.org/users/apps/).

A server-independent external component is also available - see [the 'up'
project](https://codeberg.org/inputmice/up). That project also contains a
description of the protocol between the XMPP server and the client.

This module and the protocol it implements is at an experimental prototype
stage.

Note that this module is **not related** to XEP-0357 push notifications for
XMPP. It does not send push notifications to disconnected XMPP clients. For
that, see [mod_cloud_notify](https://modules.prosody.im/mod_cloud_notify).

## Configuration

| Name                          | Description                                             | Default                                     |
|-------------------------------|---------------------------------------------------------|---------------------------------------------|
| unified_push_acl              | A list of domains or users permitted to use the service | current host, or parent host if a component |
| unified_push_backend          | Backend to use: "paseto", "storage" or "jwt"            | "paseto" (trunk), "storage" (0.12)          |
| unified_push_registration_ttl | Maximum lifetime of a push registration (seconds)       | `86400` (1 day)                             |

### Backends

The module needs to track registrations, and be able to associate tokens with
users. There are multiple ways to do this, but not every method is supported
on every Prosody version.

By default the module will automatically select the best backend that is
supported on the current Prosody version you are using.

#### storage backend

This is the default backend on Prosody 0.12 and earlier. It stores tokens and
their associated data in Prosody's configured data store.

Supported by all Prosody versions.

#### paseto backend

This is a stateless (i.e. no storage required) backend that uses encrypted
[PASETO tokens](https://paseto.io/) to store registration info. It is the
default backend on Prosody trunk, as PASETO support is not available in
Prosody 0.12 and earlier.

#### jwt backend

This is a stateless backend that uses [JWT tokens](https://jwt.io/) to store
registration info. It is supported in Prosody 0.12 and higher.

**Note:** The JWT tokens are **not encrypted**, which means the JID
associated with a registration is visible to apps and services that send you
push notifications. This can have privacy implications. If in doubt, do not
use this backend.

This backend requires you to set a secure random string in the config file,
using the `unified_push_secret` option.

A random push secret can be generated with the command
`openssl rand -base64 32`. Changing the secret will invalidate all existing
push registrations.

## HTTP configuration

This module exposes a HTTP endpoint, by default at the path `/push` (to receive push notifications from app
servers). **If you use a reverse proxy, make sure you proxy this path too.**
For more information on configuring HTTP services and reverse proxying in Prosody, see
[Prosody HTTP documentation](https://prosody.im/doc/http).

## Example configuration

### Recommended: load on Virtualhost(s)

Just add just add `"unified_push"` to your `modules_enabled` option.
This is the easiest and **recommended** configuration.

``` lua
  modules_enabled = {
    -- ...
    "unified_push";
    -- ...
  }
```

#### Component method

This is an example of how to configure the module as an internal component,
e.g. on a subdomain or other non-user domain.

This example creates a push notification component called
'notify.example.com'.

The 'http_host' line instructs Prosody to expose this module's HTTP services
on the 'example.com' host, which avoids needing to create/update DNS records
and HTTPS certificates if example.com is already set up.

``` lua
Component "notify.example.com" "unified_push"
    unified_push_secret = "<secret string here>"
    http_host = "example.com"
```

## Compatibility

  Prosody-Version   Status
  ----------------- ----------------------
  trunk             Works as of 24-12-08
  0.12              Works
