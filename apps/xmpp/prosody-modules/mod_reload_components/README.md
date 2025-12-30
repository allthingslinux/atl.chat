Introduction
============

This module allows to load/unload external components after they have
been added/removed to a configuration file. It is necessary to explicitly
initiate a reload on Prosody either via prosodyctl reload or config:reload().

Example 1:
--------
If Prosody has started with this configuration file:

``` {.lua}
VirtualHost "example.com"
    authentication = "internal_plain"

Component "a.example.com"
    component_secret = "a"

Component "b.example.com"
    component_secret = "b"
```

And the file has changed manually or dynamically to:

``` {.lua}
VirtualHost "example.com"
    authentication = "internal_plain"

Component "a.example.com"
    component_secret = "a"

Component "c.example.com"
    component_secret = "c"
```

Then, the following actions will occur if this module is loaded:

1. The component c.example.com will be loaded and start bouncing for
authentication.
2. The component b.example.com will be unloaded and deactivated. The
connection with it will not be closed, but no further actions will be
executed on Prosody.

Example 2:
--------

If Prosody has started with this configuration file:

``` {.lua}
VirtualHost "example.com"
    authentication = "internal_plain"

Component "a.example.com"
    component_secret = "a"
```

And the file has changed manually or dynamically to:

``` {.lua}
VirtualHost "example.com"
    authentication = "internal_plain"

Component "a.example.com"
    component_secret = "a"

VirtualHost "newexample.com"
        authentication = "internal_plain"

Component "a.newexample.com"
    component_secret = "a"
```

Then, the following actions will occur if this module is loaded:

1. The component a.newexample.com will be loaded and start bouncing for
authentication. Note that its respective VirtualHost is not loaded. Bad
things may happen.

Usage
=====

Copy the module folder into your Prosody modules directory. Place the
module between your enabled modules either into the global or a vhost
section.

No configuration directives are needed

Info
====

-   0.9, works
