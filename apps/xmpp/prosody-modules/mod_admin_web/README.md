---
labels:
- 'Stage-Beta'
summary: Web administration interface
rockspec:
  build:
    platforms:
      unix:
        type: command
        build_command: cd admin_web; sh get_deps.sh
        install_command: |
          cd admin_web;
          cp mod_admin_web.lua $(LUADIR);
          cp -r www_files $(PREFIX);
...

Introduction
============

This module provides a basic web administration interface. It currently
gives you access to Ad-Hoc commands on any virtual host or component
that you are set as an administrator for in the Prosody config file. It
also provides a live list of all S2S and C2S connections.

Installation
============

1.  Copy the admin\_web directory into a directory Prosody will check
    for plugins. (cf. [Installing
    modules](http://prosody.im/doc/installing_modules))
2.  Execute the contained `get_deps.sh` script from within the admin\_web
    directory. (Requires wget, tar, and a basic shell)

Configuration Details
=====================

"admin\_web" needs to be added to the modules\_enabled table of the host
you want to load this module on.

By default the interface will then be reachable under
`http://example.com:5280/admin`, or `https://example.com:5281/admin`.

The module will automatically enable two other modules if they aren't
already: mod\_bosh (used to connect to the server from the web), and
mod\_admin\_adhoc (which provides admin commands over XMPP).

    VirtualHost "example.com"
       modules_enabled = {
           .....
           "admin_web";
           .....
       }

Compatibility
=============

  --------- ---------------
  trunk     Works
  0.9       Works
  \<= 0.8   Not supported
  --------- ---------------
