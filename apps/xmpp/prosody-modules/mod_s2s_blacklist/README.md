This module lets you block connections to remote servers at the s2s
level.

``` {.lua}
modules_enabled = {
    -- other modules --
    "s2s_blacklist",

}
s2s_blacklist = {
    "proxy.eu.jabber.org",
}
```
