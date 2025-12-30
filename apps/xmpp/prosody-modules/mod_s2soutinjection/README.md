---
summary: S2S connection override
...

# Introduction

This module is similar to [mod\_srvinjection] but less of an hack.

# Configuration

``` lua
-- In the global section

modules_enabled = {
    --- your other modules
    "s2soutinjection";
}

-- targets must be IPs, not hostnames
s2s_connect_overrides = {
    -- This one will use the default port, 5269
    ["example.com"] = "1.2.3.4";

    -- To set a different port:
    ["another.example"] = { "127.0.0.1", 9999 };
}
```

# Compatibility

  Prosody version   Status
  ----------------- ---------------
  13.0.x            Should work
  0.12.4 and later  Works
  0.12.3 and older  Does not work
