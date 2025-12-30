This module adds a `portcheck` command to the [shell][doc:console]
intended for use with health checks, i.e. to check whether Prosody is
listening to all expected ports.

# Usage

After installing and enabling the module a command like this becomes
available:

``` bash
prosodyctl shell "portcheck [::]:5222 *:5222 [::]:5269 *:5269"
```

This would check if the c2s (`5222`) and s2s (`5269`) ports are
available on both IPv6 (`*`) and *Legacy IP*^[often referred to as IPv4].

# Compatibility

Compatible with Prosody **trunk**, will **not** work with 0.11.x or
earlier.
