---
labels:
- Stage-Beta
summary: "XEP-0388: Extensible SASL Profile"
---

Implementation of [XEP-0388: Extensible SASL Profile]. 

## Configuration

This module honours the same configuration options as Prosody's existing
[mod_saslauth](https://prosody.im/doc/modules/mod_saslauth).

## Developers

mod_sasl2 provides some events you can hook to affect aspects of the
authentication process:

- `advertise-sasl-features`
- `sasl2/c2s/success`
  - Priority 1000: Session marked as authenticated, success response created (`event.success`)
  - Priority -1000: Success response sent to client
  - Priority -1500: Updated <stream-features/> sent to client
- `sasl2/c2s/failure`
- `sasl2/c2s/error`

# Compatibility

This module requires Prosody **trunk** and is not compatible with 0.12 or older versions.


     Prosody Version           Status
  -----------------------  ----------------
  trunk as of 2025-05-25   Works
  13                       Works
  0.12                     Does not work
  -----------------------  ----------------
