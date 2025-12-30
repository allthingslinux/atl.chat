---
summary: Cipher policy enforcement with application level error reporting
...

# Introduction

This module arose from discussions at the XMPP Summit about enforcing
better ciphers in TLS. It may seem attractive to disallow some insecure
ciphers or require forward secrecy, but doing this at the TLS level
would the user with an unhelpful "Encryption failed" message. This
module does this enforcing at the application level, allowing better
error messages.

# Configuration

First, download and add the module to `module_enabled`.  Then you can
decide on what policy you want to have.

Requiring ciphers with forward secrecy is the most simple to set up.

``` lua
tls_policy = "FS" -- allow only ciphers that enable forward secrecy
```

A more complicated example:

``` lua
tls_policy = {
  c2s = {
    encryption = "AES"; -- Require AES (or AESGCM) encryption
    protocol = "TLSv1.2"; -- and TLSv1.2
    bits = 128; -- and at least 128 bits (FIXME: remember what this meant)
  }
  s2s = {
    cipher = "AESGCM"; -- Require AESGCM ciphers
    protocol = "TLSv1.[12]"; -- and TLSv1.1 or 1.2
    authentication = "RSA"; -- with RSA authentication
  };
}
```

# Compatibility

Requires LuaSec 0.5

