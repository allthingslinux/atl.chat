---
labels:
- 'Stage-Obsolete'
summary: 'Replacement for mod\_vcard with vcard4 support and PEP integration'
superseded_by: mod_vcard_legacy
---

::: {.alert .alert-warning}
[mod\_vcard\_legacy][doc:modules:mod_vcard_legacy] and
[mod\_vcard4][doc:modules:mod_vcard4] included with Prosody 0.11.x
provide equivalent functionality.
:::

# Introduction

This module was an experimental replacement for [mod\_vcard]. In addition to
the ageing protocol defined by [XEP-0054], it also supports the [new
vCard 4 based protocol][xep0292] and integrates with [Personal
Eventing Protocol][xep0163].

Also supports [XEP-0398: User Avatar to vCard-Based Avatars Conversion].

The vCard 4, [User Avatar][xep0084] and [User Nickname][xep0172]
PEP nodes are updated when the vCard is changed..

# Configuration

    modules_enabled = {
        -- "vcard";  -- This module must be removed

        "profile";
    }

# Compatibility

Requires Prosody **trunk** as of 2014-05-29. Won't work in 0.10.x.

It depends on the trunk version of [mod\_pep][doc:modules:mod_pep] for PEP support, 
previously known as [mod\_pep\_plus][doc:modules:mod_pep_plus].
