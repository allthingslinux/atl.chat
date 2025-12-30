---
summary: 'Module for testing ad-hoc commands and dataforms rendering'
---

# Introduction

This module provides [Ad-Hoc commands][xep0050] for testing [data
form][xep0004] that includes all kinds of fields. It's meant to help
debug both Prosodys
[`util.dataforms`][doc:developers:util:dataforms] library and
clients, eg seeing how various field types are rendered.

# Configuration

Simply add it to [`modules_enabled`][doc:modules_enabled] like any
other module.

``` {.lua}
modules_enabled = {
    -- All your other modules etc
    "adhoc_dataforms_demo";
}
```

# Usage

In your Ad-Hoc capable client, first look for "Execute command". You
should see a form with various kinds of fields.

Dataforms Demo
:   A simple command that provides a dataform with every possible field
    type, suitable for testing rending of dataforms.

Multi-step command demo
:   A command that has multiple steps, suitable for testing back and
    forwards navigation.
