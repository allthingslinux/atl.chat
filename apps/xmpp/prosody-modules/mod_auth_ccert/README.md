---
labels:
- 'Stage-Alpha'
- 'Type-Auth'
summary: Client Certificate authentication module
...

Introduction
============

This module implements PKI-style client certificate authentication. You
will therefore need your own Certificate Authority. How to set that up
is beyond the current scope of this document.

Configuration
=============


    authentication = "ccert"
    certificate_match = "xmppaddr" -- or "email"

    c2s_ssl = {
        cafile = "/path/to/your/ca.pem";
        capath = false; -- Disable capath inherited from built-in default
        verify = {"peer"; "client_once"}; -- Ask for client certificate
        verifyext = {
            -- Don't validate client certs as if they were server certs
            lsec_ignore_purpose = false
        }
    }


Compatibility
=============

  ----------------- --------------
  trunk             Works
  0.10 and later    Works
  0.9 and earlier   Doesn't work
  ----------------- --------------
