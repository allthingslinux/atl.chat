# Introduction

::: {.alert .alert-danger}
Consider using [mod_mam][doc:modules:mod_mam] together with
[mod_readonly] instead.
:::

This module logs messages to a SQL database.

SQL connection options are configured in a `message_log_sql` option,
which has the same syntax as the `sql` option for
[mod_storage_sql][doc:modules:mod_storage_sql].

# Usage

You will need to create the following table in the configured database:

``` sql
CREATE TABLE `prosodyarchive` (
        `host` TEXT,
        `user` TEXT,
        `store` TEXT,
        `id` INTEGER PRIMARY KEY AUTOINCREMENT,
        `when` INTEGER,
        `with` TEXT,
        `resource` TEXT,
        `stanza` TEXT);
```

# Compatibility

Does *NOT* work with 0.10 due to a conflict with the new archiving
support in `mod_storage_sql`·
