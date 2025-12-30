---
description: File management for uploaded files
labels:
- Stage-Alpha
---

Introduction
============

This module exposes ad-hoc commands [XEP-0050] for listing uploaded files, and
later for managing them.

Configuration
=============

This module depends on mod\_http\_upload, and exposes ad-hoc commands for each
operation a user might do on their uploaded files.

The module can be added to the `modules_enabled` field on a host on which
mod\_http\_upload is loaded.

Compatibility
=============

Works with Prosody trunk at least.
