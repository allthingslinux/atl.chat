---
labels:
- 'Stage-Obsolete'
summary: Telnet command for showing TLS info
---

Introduction
============

This module adds two commands to the telnet console, `c2s:showtls()` and
`s2s:showtls()`. These commands shows TLS parameters, such as ciphers
and key agreement protocols, of all c2s or s2s connections.

Configuration
=============

Just add the module to the `modules_enabled` list. There is no other
configuration.

    modules_enabled = {
        ...
        "telnet_tlsinfo";
    }

Usage
=====

Simply type `c2s:showtls()` to show client connections or
`s2s:showtls()` for server-to-server connections. These commands can
also take a JID for limiting output to matching users or servers.

    s2s:showtls("prosody.im")
    | example.com   ->  prosody.im
    |             protocol: TLSv1.1
    |               cipher: DHE-RSA-AES256-SHA
    |           encryption: AES(256)
    |              algbits: 256
    |                 bits: 256
    |       authentication: RSA
    |                  key: DH
    |                  mac: SHA1
    |               export: false

  Field            Description
  ---------------- -------------------------------------------------------------------------------------------------
  protocol         The protocol used. **Note**: With older LuaSec, this is the protocol that added the used cipher
  cipher           The OpenSSL cipher string for the currently used cipher
  encryption       Encryption algorithm used
  bits, algbits    Secret bits involved in the cipher
  authentication   The authentication algorithm used
  mac              Message authentication algorithm used
  key              Key exchange mechanism used.
  export           Whethere an export cipher is used

Compatibility
=============

  --------------------- ------------------
  0.9 with LuaSec 0.5   Works
  0.10                  Merged into core
  --------------------- ------------------
