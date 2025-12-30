---
labels:
- 'Stage-Alpha'
summary: Security Labels
...

Introduction
============

This module implements [XEP-0258: Security Labels in XMPP], but not
actual policy enforcement. See for example [mod_firewall] for that.

Configuration
=============

As with all modules, you enable it by adding it to the modules\_enabled
list.

These options exist:

  Name                      Description             Default
  ------------------------- ----------------------- -------------
  security\_catalog\_name   Catalouge name          "Default"
  security\_catalog\_desc   Catalouge description   "My labels"

You can then add your labels in a table called security\_labels. They
can be both orderd and unorderd, but ordered comes first.

``` {.lua}
security_labels = {
  { -- This label will come first
    name = "Public",
    label = true, -- This is a label, but without the actual label.
      default = true -- This is the default label.
  },
  {
    name = "Private",
    label = "PRIVATE",
    color = "white",
    bgcolor = "blue"
  },
  Sensitive = { -- A Sub-selector
    SECRET = { -- The index is used as name
      label = true
    },
    TOPSECRET = { -- The order of this and the above is not guaranteed.
      color = "red",
      bgcolor = "black",
    }
  }
}
```

Each label can have the following properties:

  Name             Description                                               Default
  ---------------- --------------------------------------------------------- ----------------------------------------------------------
  name             The name of the label. Used for selector.                 Required.
  label            The actual label, ie `<esssecuritylabel/>`                Required, can be boolean for a empty label, or a string.
  display          The text shown as display marking.                        Defaults to the name
  color, bgcolor   The fore- and background color of the display marking     None
  default          Boolean, true for the default. Only one may be default.   false
