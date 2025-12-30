---
labels:
- 'Stage-Merged'
- 'Type-Auth'
summary: LDAP authentication module
...

Introduction
============

This is a Prosody authentication plugin which uses LDAP as the backend.

Dependecies
===========

This module depends on [LuaLDAP](https://github.com/lualdap/lualdap)
for connecting to an LDAP server.

Configuration
=============

Copy the module to the prosody modules/plugins directory.

In Prosody's configuration file, under the desired host section, add:

``` {.lua}
authentication = "ldap"
ldap_base = "ou=people,dc=example,dc=com"
```

Further LDAP options are:

  Name                  Description                                                                                                            Default value
  --------------------- ---------------------------------------------------------------------------------------------------------------------- --------------------
  ldap\_base            LDAP base directory which stores user accounts                                                                         **Required field**
  ldap\_server          Space-separated list of hostnames or IPs, optionally with port numbers (e.g. "localhost:8389")                         `"localhost"`
  ldap\_rootdn          The distinguished name to auth against                                                                                 `""` (anonymous)
  ldap\_password        Password for rootdn                                                                                                    `""`
  ldap\_filter          Search filter, with `$user` and `$host` substituted for user- and hostname                                             `"(uid=$user)"`
  ldap\_scope           Search scope. other values: "base" and "onelevel"                                                                      `"subtree"`
  ldap\_tls             Enable TLS (StartTLS) to connect to LDAP (can be true or false). The non-standard 'LDAPS' protocol is not supported.   `false`
  ldap\_mode            How passwords are validated.                                                                                           `"bind"`
  ldap\_admin\_filter   Search filter to match admins, works like ldap\_filter

**Note:** lua-ldap reads from `/etc/ldap/ldap.conf` and other files like
`~prosody/.ldaprc` if they exist. Users wanting to use a particular TLS
root certificate can specify it in the normal way using TLS\_CACERT in
the OpenLDAP config file.

Modes
=====

The `"getpasswd"` mode requires plain text access to passwords in LDAP
and feeds them into Prosodys authentication system. This enables more
secure authentication mechanisms but does not work for all deployments.

The `"bind"` mode performs an LDAP bind, does not require plain text
access to passwords but limits you to the PLAIN authentication
mechanism.

Compatibility
=============

Works with 0.8 and later.
