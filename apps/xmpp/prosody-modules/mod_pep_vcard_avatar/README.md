---
labels:
- 'Stage-Alpha'
summary: Sync avatars between vCards and PEP
---

## Introduction

This module pushes the users nickname and avatar from vCards into PEP,
or into vCards from PEP. This allows interop between older clients that
use [XEP-0153: vCard-Based Avatars] to see the avatars of clients that
use [XEP-0084: User Avatar] and vice versa.

Also see [XEP-0398: User Avatar to vCard-Based Avatars Conversion].

## Configuration

Simply [enable it like most other modules][doc:installing_modules#prosody-modules],
no further configuration needed.

## Compatibility

  ------- --------------------------------
  trunk   Use mod\_vcard\_legacy instead
  0.11    Use mod\_vcard\_legacy instead
  0.10    Works
  0.9     Does not work
  0.8     Does not work
  ------- --------------------------------
