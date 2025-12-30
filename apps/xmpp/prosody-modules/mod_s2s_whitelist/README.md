This module lets you block connections to any remote servers not on a
whitelist.

``` {.lua}
modules_enabled = {
    -- other modules --
    "s2s_whitelist",

}
s2s_whitelist = {
    "example.org",
}
```
