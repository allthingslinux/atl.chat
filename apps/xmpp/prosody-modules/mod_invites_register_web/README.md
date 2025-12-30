---
labels:
- 'Stage-Beta'
summary: 'Register accounts via the web using invite tokens'
rockspec:
  dependencies:
  - mod_invites_page
  - mod_password_policy
  - mod_register_apps
  build:
    copy_directories:
    - html
...

Introduction
============

This module is part of the suite of modules that implement invite-based
account registration for Prosody. The other modules are:

- [mod_invites]
- [mod_invites_adhoc]
- [mod_invites_page]
- [mod_invites_register]
- [mod_invites_api]
- [mod_register_apps]

For details and a full overview, start with the [mod_invites] documentation.

Details
=======

mod_invites_register_web implements a web-based registration form that
validates invite tokens. It also supports guiding the user through client
download and configuration via mod_register_apps.

The optional `site_name` setting can be used to override the displayed site name.

```lua
site_name = "My Chat Service"
```

HTML templates can be overridden by using `invites_register_template_path`, see the `html/` directory in the sources for the files needed.

```lua
invites_register_template_path = "/path/to/templates/html"
```


You may also set `webchat_url` to the URL of a web chat that will be linked
to after successful registration. If not specified but [mod_conversejs] is loaded
on the current host, it will default to the URL of that module.

This module depends on [mod_invites_page] solely for the case where an invalid
invite token is received - it will redirect to mod_invites_page so that an
appropriate error can be served to the user.

The module also depends on [mod_password_policy] (which will be automatically
loaded). As a consequence of this module being loaded, the default password
policies will be enforced for all registrations on the server if not
explicitly loaded or configured.

Compatibility
=============

Prosody-Version Status
--------------- ---------------------
trunk           Works as of 24-12-08
0.12            Works
