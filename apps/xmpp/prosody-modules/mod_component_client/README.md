Introduction
============

This module turns Prosody hosts into components of other XMPP servers.

Configuration
=============

Example configuration:

``` {.lua}
VirtualHost "component.example.com"
modules_enabled = { "component_client" }
component_client = {
    host = "localhost";
    port = 5347;
    secret = "hunter2";
}
```
