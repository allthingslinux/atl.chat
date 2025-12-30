---
labels:
- 'Stage-Beta'
summary: 'Serve a welcome page to users'
rockspec:
  dependencies:
  - mod_http_libjs
  build:
    copy_directories:
    - html
...

Introduction
============

This module serves a welcome page to users, and allows them to create an
account invite via the web on invite-only servers.

The page template and policy of when to allow account creation are both
possible to override.

This module is part of the suite of modules that implement invite-based
account registration for Prosody. The other modules are:

- mod_invites
- mod_invites_adhoc
- mod_invites_page
- mod_invites_register
- mod_invites_register_web
- mod_register_apps

For details and a full overview, start with the mod_invites documentation.

Configuration
=======

`welcome_page_template_path`
:   The path to a directory containing the page templates and assets. See
    the module source for the example template.

`welcome_page_variables`
:   Optional variables to pass to the template, available as `{var.name}`

`welcome_page_open_registration`
:   Whether to allow account creation in the absence of any other plugin
    overriding the policy. Defaults to `false` unless `registration_invite_only`
    is set to `false`.
