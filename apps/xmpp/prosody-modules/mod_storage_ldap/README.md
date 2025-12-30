---
labels:
- 'Type-Storage'
summary: 'LDAP storage for rosters, groups, and vcards'
...

Introduction
============

See [mod\_lib\_ldap](mod_lib_ldap.html) for more information.

Installation
============

You must install [mod\_lib\_ldap](mod_lib_ldap.html) to use this module.
After that, you need only copy mod\_storage\_ldap.lua and
ldap/vcard.lib.lua to your Prosody installation's plugins directory.
Make sure vcard.lib.lua is installed under plugins/ldap/.

Configuration
=============

In addition to the configuration that [mod\_lib\_ldap](mod_lib_ldap.html)
itself requires, this plugin also requires the following fields in the
ldap section:

-   user.namefield
-   groups.memberfield
-   groups.namefield
-   groups.basedn
-   vcard\_format (optional)

See the README.html distributed with [mod\_lib\_ldap](mod_lib_ldap.html) for
details.
