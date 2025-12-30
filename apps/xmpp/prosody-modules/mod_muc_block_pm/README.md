---
summary: Prevent MUC participants from sending PMs
---

# Introduction

This module prevents *participants* from sending private messages to
anyone except *moderators*.

# Configuration

The module doesn't have any options, just load it onto a MUC component.

``` lua
Component "muc"
modules_enabled = {
    "muc_block_pm";
}
```

# Compatibility

    Branch State
  -------- -----------------
      0.11 Will **not** work
      0.12 Should work
