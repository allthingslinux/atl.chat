---
labels:
- 'Stage-Alpha'
- 'Type-Auth'
summary: PHPBB3 authentication module
...

Introduction
============

This module allows you to authenticate against an PHPBB3 database.

To support the `bcrypt` password hashing algorithm, install
[bcrypt](https://luarocks.org/modules/mikejsavage/bcrypt) from luarocks:

    luarocks install bcrypt

Configuration
=============

SQL connection paramaters are identical to those of [SQL
storage](https://prosody.im/doc/modules/mod_storage_sql).

    authentication = "phpbb3"
    sql = { -- See documentation for SQL storage
        driver = "MySQL";
        database = "phpbb3";
        host = "localhost";
        username = "prosody";
        password = "secretpassword";
    }

Compatibility
=============

Prosody 0.8+
