---
labels:
- 'Stage-Alpha'
summary: 'XEP-0474: SASL SCRAM Downgrade Protection'
...

Introduction
============

This module implements the experimental XEP-0474: SASL SCRAM Downgrade
Protection. It provides an alternative downgrade protection mechanism to
client-side pinning which is currently the most common method of downgrade
protection.

# Configuration

There are no configuration options for this module, just load it as normal.

# Compatibility

  Prosody-Version Status
  --------------- ----------------------
  trunk           Works as of 2025-05-25
  13              Works
  0.12            Does not work
