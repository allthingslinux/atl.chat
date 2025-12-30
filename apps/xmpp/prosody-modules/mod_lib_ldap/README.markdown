---
labels:
summary: Library module for LDAP
...

Introduction
============

This module is used by other modules to access an LDAP server. It's
pretty useless on its own; you should use it if you want to write your
own LDAP-related module, or if you want to use one of mine
([mod\_auth\_ldap2](mod_auth_ldap2.html),
[mod\_storage\_ldap](mod_storage_ldap.html)).

Installation
============

Simply copy ldap.lib.lua into your Prosody installation's plugins
directory.

Configuration
=============

Configuration for this module (and all modules that use it) goes into
the *ldap* section of your prosody.cfg.lua file. Each plugin that uses
it may add their own sections; this plugin relies on the following keys:

-   hostname - Where your LDAP server is located
-   bind\_dn - The DN to perform queries as
-   bind\_password - The password to use for queries
-   use\_tls - Whether or not TLS should be used to connect to the LDAP
    server
-   user.usernamefield - The LDAP field that contains a user's username
-   user.basedn - The base DN for user records

API
===

ldap.getconnection()
--------------------

Returns an LDAP connection object corresponding to the configuration in
prosody.cfg.lua. The connection object is a
[LuaLDAP](http://www.keplerproject.org/lualdap/) connection.

ldap.getparams()
----------------

Returns the LDAP configuration provided in prosody.cfg.lua. Use this if
you want to stick some configuration information for your module into
the LDAP section in the configuration file.

ldap.bind(username, password)
-----------------------------

Verifies that *username* and *password* bind ok. **NOTE**: This does not
bind the current LDAP connection to the given username!

ldap.singlematch(query)
-----------------------

Used to fetch a single LDAP record given an LDAP query. A convenience
function.

ldap.filter.combine\_and(...)
-----------------------------

Takes a list of LDAP filter expressions and returns a filter expression
that results in the intersection of each given expression (it ANDs them
together).

More Information
================

For more information, please consult the README.html file under
prosody-modules/mod\_lib\_ldap.
