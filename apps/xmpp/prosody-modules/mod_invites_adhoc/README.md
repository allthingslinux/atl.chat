---
labels:
- 'Stage-Merged'
summary: 'Enable ad-hoc command for XMPP clients to create invitations'
...

Introduction
============

::: {.alert .alert-info}
This module has been merged into Prosody as
[mod_invites_adhoc][doc:modules:mod_invites_adhoc]. Users of Prosody **0.12**
and later should not install this version.
:::

This module is part of the suite of modules that implement invite-based
account registration for Prosody. The other modules are:

- [mod_invites][doc:modules:mod_invites]
- [mod_invites_register][doc:modules:mod_invites_register]
- [mod_invites_page]
- [mod_invites_register_web]
- [mod_invites_api]
- [mod_register_apps]

For details and a full overview, start with the [mod_invites] documentation.

Details
=======

mod_invites_adhoc allows XMPP clients to create new invites on the server.
Clients must support either XEP-0401 (Easy Onboarding) or XEP-0050 (Ad-hoc
commands).

There are three types of invitation that can be created:

| Invite type | Description |
|--|--|
| Account-only invites | These can be used to register a new account |
| Contact-only invites | These can be shared with a contact so they can easily add you to their contact list |
| Account-and-contact invites | Like a contact-only invite, but also allows the contact to register on the current server if they don't already have an XMPP account |

Only configured admins of the server are able to create account-only invites. By default
normal users may only create contact-only invites, but account-and-contact invites can
be enabled with the `allow_user_invites` option.

Configuration
=============

| Name                  | Description                                                           | Default                                   |
|-----------------------|-----------------------------------------------------------------------|-------------------------------------------|
| allow_user_invites    | Whether non-admin users can invite contacts to register on this server| `false`                                   |
| allow_contact_invites | Whether non-admin users can invite contacts to their roster           | `true`                                    |

The `allow_user_invites` option should be set as desired. However it is
strongly recommended to leave the other option (`allow_contact_invites`)
at its default to provide the best user experience.
