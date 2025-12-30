---
labels:
- 'Type-S2SAuth'
---

Introduction
============

[PKIX over Secure HTTP (POSH)][rfc7711] describes a method of
securely delegating a domain to a hosting provider, without that hosting
provider needing keys and certificates covering the hosted domain.

# Validating

This module performs POSH validation of other servers. It is *not*
needed to delegate your own domain.

# Delegation

You can generate the JSON delegation file from a certificate by running
`prosodyctl mod_s2s_auth_posh /path/to/example.crt`. This file needs to
be served at `https://example.com/.well-known/posh/xmpp-server.json`.
