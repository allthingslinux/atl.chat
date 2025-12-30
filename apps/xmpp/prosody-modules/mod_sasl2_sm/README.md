---
labels:
- Stage-Beta
summary: "XEP-0198 integration with SASL2"
rockspec:
  dependencies:
  - mod_sasl2
  - mod_sasl2_bind2
---

Add support for inlining stream management negotiation into the SASL2 process. (See [XEP-0388: Extensible SASL Profile])

This module depends on [mod_sasl2] and [mod_sasl2_bind2]. It exposes no
configuration options.

# Compatibility

  Prosody-Version Status
  --------------- ----------------------
  trunk           Works as of 2025-05-25
  13              Work
  0.12            Does not work
