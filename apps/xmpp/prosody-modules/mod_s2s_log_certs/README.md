---
summary: Log certificate status and fingerprint of remote servers
...

Introduction
============

This module produces info level log messages with the certificate status
and fingerprint every time an s2s connection is established. It can also
optionally store this in persistent storage.

**info** jabber.org has a trusted valid certificate with SHA1:
11:C2:3D:87:3F:95:F8:13:F8:CA:81:33:71:36:A7:00:E0:01:95:ED

Fingerprints could then be added to
[mod\_s2s\_auth\_fingerprint](mod_s2s_auth_fingerprint.html).

Configuration
=============

Add the module to the `modules_enabled` list.

    modules_enabled = {
        ...
        "s2s_log_certs";
    }

If you want to keep track of how many times, and when a certificate is
seen add

`s2s_log_certs_persist = true`

Compatibility
=============

  ------- --------------
  trunk   Works
  0.10    Works
  0.9     Works
  0.8     Doesn't work
  ------- --------------
