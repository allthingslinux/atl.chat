# Introduction

This module adds support for advertising the language used in a room.

# Configuring

``` {.lua}
Component "rooms.example.net" "muc"
modules_enabled = {
    "muc_lang";
}
```

The room language is specified in a new field in the room configuration
dialog, accessible through compatible clients.

Use [language codes](https://en.wikipedia.org/wiki/ISO_639) like `en`,
`fr`, `de` etc.

# Compatibility

Meant for use with Prosody 0.10.x

Native support was [added in Prosody
trunk/0.11](https://hg.prosody.im/trunk/rev/9c90cd2fc4c3), so there is
no need for this module.
