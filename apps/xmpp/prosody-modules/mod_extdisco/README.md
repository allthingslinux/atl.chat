---
summary: External Service Discovery
...

Introduction
============

This module adds support for [XEP-0215: External Service Discovery],
which lets Prosody advertise non-XMPP services.

Configuration
=============

Example services from the XEP:

``` {.lua}
modules_enabled = {
    -- other modules ...
    "extdisco";
}

external_services = {
    ["stun.shakespeare.lit"] = {
        port="9998";
        transport="udp";
        type="stun";
    };
    ["relay.shakespeare.lit"] = {
        password="jj929jkj5sadjfj93v3n";
        port="9999";
        transport="udp";
        type="turn";
        username="nb78932lkjlskjfdb7g8";
    };
    ["192.0.2.1"] = {
        port="8888";
        transport="udp";
        type="stun";
    };
    ["192.0.2.1"] = {
        port="8889";
        password="93jn3bakj9s832lrjbbz";
        transport="udp";
        type="turn";
        username="auu98sjl2wk3e9fjdsl7";
    };
    ["ftp.shakespeare.lit"] = { 
        name="Shakespearean File Server";
        password="guest";
        port="20";
        transport="tcp";
        type="ftp";
        username="guest";
    };
}
```

Compatibility
=============

Incompatible with
[mod_turncredentials](https://modules.prosody.im/mod_turncredentials).
