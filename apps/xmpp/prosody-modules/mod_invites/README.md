---
labels:
- 'Stage-Merged'
summary: 'Invite management module for Prosody'
...

Introduction
============

::: {.alert .alert-info}
This module has been merged into Prosody as
[mod_invites][doc:modules:mod_invites]. Users of Prosody **0.12**
and later should not install this version.
:::

This module is part of the suite of modules that implement invite-based
account registration for Prosody. The other modules are:

- [mod_invites_adhoc][doc:modules:mod_invites_adhoc]
- [mod_invites_register][doc:modules:mod_invites_register]
- [mod_invites_page]
- [mod_invites_register_web]
- [mod_invites_api]
- [mod_register_apps]

This module manages the creation and consumption of invite codes for the
host(s) it is loaded onto. It currently does not expose any admin/user-facing
functionality (though in the future it will probably gain a way to view/manage
pending invites).

Instead, other modules can use the API from this module to create invite tokens
which can be used to e.g. register accounts or create automatic subscription
approvals.

This module should not be confused with the similarly named mod_invite (note the
missing 's'!). That module was a precursor to this one that helped test and prove
the concept of invite-based registration, and is now deprecated.

# Configuration

This module exposes just one option - the length of time that a generated invite
should be valid for by default.

``` {.lua}
-- Configure the number of seconds a token is valid for (default 7 days)
invite_expiry = 86400 * 7
```

# Invites setup

For a fully-featured invite-based setup, the following provides an example
configuration:

``` {.lua}
-- Specify the external URL format of the invite links

VirtualHost "example.com"
    invites_page = "https://example.com/invite?{invite.token}"
    http_external_url = "https://example.com/"
    http_paths = {
        invites_page = "/invite";
        invites_register_web = "/register";
    }
    modules_enabled = {
        "invites";
        "invites_adhoc";
        "invites_page";
        "invites_register";
        "invites_register_web";

        "http_libjs"; -- See 'external dependencies' below
    }
```

Restart Prosody and create a new invite using an ad-hoc command in an XMPP client connected
to your admin account, or use the command line:

    prosodyctl mod_invites generate example.com

## External dependencies

The default HTML templates for the web-based modules depend on some CSS and Javascript
libraries. They expect these to be available at `https://example.com/share`. An easy
way of doing this if you are on Debian 10 (buster) is to enable mod_http_libjs and install
the following packages:

    apt install libjs-bootstrap4 libjs-jquery

On other systems you will need to manually put these libraries somewhere on the filesystem
that Prosody can read, and serve them using mod_http_libjs with a custom `libjs_path`
setting.

# Compatibility

0.11 and later.
