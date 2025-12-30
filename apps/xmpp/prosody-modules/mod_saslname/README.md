---
labels:
- 'Stage-Stable'
- 'Type-Auth'
summary: 'XEP-0233: XMPP Server Registration for use with Kerberos V5'
...

Introduction
============

This module implements a manual method for advertsing the Kerberos
principal name as per [XEP-0233]. It could be used in conjection with
a Kerberos authentication module.

Configuration
=============

    sasl_hostname = "auth42.us.example.com"

Compatibility
=============

Prosody 0.7+
