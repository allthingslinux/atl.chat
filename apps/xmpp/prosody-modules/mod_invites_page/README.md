---
labels:
- 'Stage-Beta'
summary: 'Generate friendly web page for invitations'
rockspec:
  dependencies:
  - mod_register_apps
  build:
    copy_directories:
    - html
    - static
...

Introduction
============

This module is part of the suite of modules that implement invite-based
account registration for Prosody. The other modules are:

- [mod_invites]
- [mod_invites_adhoc]
- [mod_invites_register]
- [mod_invites_register_web]
- [mod_invites_api]
- [mod_register_apps]

For details and a full overview, start with the [mod_invites] documentation.

Details
=======

mod_invites_page provides a unique web page for each generated invitation.
Without this module, Prosody will only be able to generate invite links as
`xmpp:` URIs (they look something like `xmpp:example.com?register;preauth=29Xbxr91`).
URIs will only work if the invited user already has an XMPP client installed.
This is usually not the case.

This module transforms the URI into a friendly web page that can be shared
via any method (email, SMS, etc.), and opened in any browser. The page explains
the invitation and guides the user to set up their account using one of a
configurable list of XMPP clients (to configure the list, see mod_register_apps
documentation).

For a complete experience one should also load
[mod_invites_register], [mod_invites_register_web], [mod_register_apps] and [mod_http_libjs] see [mod_invites]

Configuration
=============

| Name                      | Description                                                                    | Default                                             |
|---------------------------|--------------------------------------------------------------------------------|-----------------------------------------------------|
| invites_page              | The format of an invite page URL (must begin with `https://`)                  | `"https://{host}:5281/invites_page?{invite.token}"` |
| invites_registration_page | The format of an invite registration page URL (may be relative to invites_page)| `"register?t={invite.token}&c={app.id}"`            |
| site_name                 | The friendly name of the server                                                | `"example.com"`                                     |
| invites_page_external     | Set this to true if your invitation pages will be rendered by something else   | `false`                                             |

The `invites_page` and `invites_registration_page` options are templates
that support a number of variables. The most useful being `{host}` and
`{invite.token}`.

All the usual [HTTP configuration options](https://prosody.im/doc/http)
can be used to configure this module. In particular, if you run Prosody
behind a reverse proxy such as nginx or Apache, you will probably want
to set `http_external_url` so that Prosody knows what URLs should look
like for users.

If you want to disable this module's built-in pages and use an external
invitation page generator (such as [ge0rg/easy-xmpp-invitation](https://github.com/ge0rg/easy-xmpp-invitation)
then set `invites_page_external = true` and set `invites_page` to the
appropriate URL for your installation.

Compatibility
=============

  Prosody-Version Status
  --------------- ---------------------
  trunk           Works as of 24-12-08
  0.12            Works
