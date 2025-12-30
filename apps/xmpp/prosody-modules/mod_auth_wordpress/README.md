---
labels:
- 'Stage-Alpha'
- 'Type-Auth'
summary: Wordpress authentication module
...

Introduction
============

This module allows you to authenticate against an Wordpress database.

Configuration
=============

SQL connection paramaters are identical to those of [SQL
storage](https://prosody.im/doc/modules/mod_storage_sql).

    authentication = "wordpress"
    wordpress_table_prefix = "wp_" -- default table prefix
    sql = { -- See documentation for SQL storage
        driver = "MySQL";
        database = "my_wordpress";
        host = "localhost";
        username = "prosody";
        password = "secretpassword";
    }

Compatibility
=============

Prosody 0.8+
