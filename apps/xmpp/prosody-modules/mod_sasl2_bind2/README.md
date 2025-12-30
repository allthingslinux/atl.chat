---
labels:
- Stage-Beta
summary: "Bind 2 integration with SASL2"
rockspec:
  dependencies:
  - mod_sasl2
---

Add support for [XEP-0386: Bind 2], which is a new method for clients to bind
resources and establish sessions in XMPP, using SASL2. 

This module depends on [mod_sasl2]. It exposes no configuration options.

# Compatibility

  Prosody-Version Status
  --------------- ----------------------
  trunk           Works as of 2025-05-25
  13              Works
  0.12            Does not work
