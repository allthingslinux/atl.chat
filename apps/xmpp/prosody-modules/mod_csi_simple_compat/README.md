# About

This module allows using the [mod_csi_simple][doc:modules:mod_csi_simple]
setting `csi_important_payloads` (added in trunk/0.12) in Prosody 0.11.x.

# Config

```
modules_enabled = {
    -- other modules etc
    "csi_simple",
    "csi_simple_compat",
}

csi_important_payloads = {
    -- Anything in this namespace:
    "{urn:example:important-namespace}",
    -- Specific element name and namespace:
    "{urn:example:xmpp:priority}super-important",
}
```

# Example

``` lua
csi_important_payloads = {
    -- XEP-0353: Jingle Message Initiation
    "{urn:xmpp:jingle-message:0}",
}
```

