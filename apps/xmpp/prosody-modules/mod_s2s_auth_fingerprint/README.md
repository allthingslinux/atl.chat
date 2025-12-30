---
labels:
- 'Stage-Alpha'
- 'Type-S2SAuth'
summary: Fingerprint based s2s authentication
...

Introduction
============

This module allows you to manually pin certificate fingerprints of
remote servers.

Details
=======

Servers not listed in the configuration are not affected.

Configuration
=============

After installing and enabling this module, you can put fingerprints of
remote servers in your config like this:

``` {.lua}
s2s_auth_fingerprint_digest = "sha1" -- This is the default. Other options are "sha256" and "sha512"
s2s_trusted_fingerprints = {
    ["jabber.org"] = "11:C2:3D:87:3F:95:F8:13:F8:CA:81:33:71:36:A7:00:E0:01:95:ED";
    ["matthewwild.co.uk"] = {
        "FD:7F:B2:B9:4C:C4:CB:E2:E7:48:FB:0D:98:11:C7:D8:4D:2A:62:AA";
        "CF:F3:EC:43:A9:D5:D1:4D:D4:57:09:55:52:BC:5D:73:06:1A:A1:A0";
    };
}

-- If you don't want to fall back to dialback, you can list the domains s2s_secure_domains too
s2s_secure_domains = {
    "jabber.org";
}
```

Compatibility
=============

  ------- --------------
  trunk   Works
  0.9     Works
  0.8     Doesn't work
  ------- --------------
