# Introduction

Many projects have a support room accessible via a web chat. This module
allows making the URL to such a web chat discoverable via the XMPP
service discovery protocol, enabling e.g. [search
engines](https://search.jabbercat.org/) to index and present these.

# Configuring

## Enabling

``` {.lua}
Component "rooms.example.net" "muc"
modules_enabled = {
    "muc_webchat_url";
}
```

## Settings

The URL is configured using the in-band MUC room configuration protocol.

The module can optionally be configured to give all public (not
members-only, hidden or password protected) rooms gain a default value
based on a template:

``` {.lua}
muc_webchat_baseurl = "https://chat.example.com/join?room={node}"
```

The following variables will be subsituted with room address details:

`{jid}`
:   The complete room address, eg `room@muc.example.com`·

`{node}`
:   The local part (before the `@`) of the room JID.

`{host}`
:   The domain name part of the room JID.
