---
labels:
- Stage-Beta
summary: "Fast Authentication Streamlining Tokens"
rockspec:
  dependencies:
  - mod_sasl2
---

This module implements a mechanism described in [XEP-0484: Fast Authentication Streamlining Tokens] via which clients can exchange a
password for a secure token, improving security and streamlining future reconnections.

This module depends on [mod_sasl2].

## Configuration

| Name                      | Description                                            | Default               |
|---------------------------|--------------------------------------------------------|-----------------------|
| sasl2_fast_token_ttl      | Default token expiry (seconds)                         | 86400*21 (21 days)  |
| sasl2_fast_token_min_ttl  | Time before tokens are eligible for rotation (seconds) | 86400 (1 day)       |

The `sasl2_fast_token_ttl` option determines the length of time a client can
remain disconnected before being "logged out" and needing to authenticate with
a password. Clients must perform at least one FAST authentication within this
period to remain active.

The `sasl2_fast_token_min_ttl` option defines how long before a token will be
rotated by the server. By default a token is rotated if it is older than 24
hours. This value should be less than `sasl2_fast_token_ttl` to prevent
clients being logged out unexpectedly.

# Compatibility

  Prosody-Version Status
  --------------- ----------------------
  trunk           Works as of 2025-05-25
  13              Work
  0.12            Does not work
