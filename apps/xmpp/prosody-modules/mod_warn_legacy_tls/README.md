---
labels:
- Stage-Alpha
summary: Warn users of obsolete TLS Versions in clients
---

TLS 1.0 and TLS 1.1 are obsolete. This module warns clients if they are using those versions, to prepare for disabling them. (If you use the default prosody config, this module will be unnessesary in its default setting, since these protocols are not allowed anymore by any supported prosody version.)

This module can be used to warn from TLS1.2 if you want to switch to modern security in the near future.

# Configuration

``` lua
modules_enabled = {
    -- other modules etc
    "warn_legacy_tls";
}

-- This is the default, you can leave it out if you don't wish to
-- customise or translate the message sent.
-- '%s' will be replaced with the TLS version in use.
legacy_tls_warning = [[
Your connection is encrypted using the %s protocol, which has been demonstrated to be insecure and will be disabled soon.  Please upgrade your client.
]]

--You may want to warn about TLS1.2 these days too (This note added 2024), by default prosody will not even allow connections from TLS <1.2
--Example:
legacy_tls_versions = { "TLSv1", "TLSv1.1", "TLSv1.2" }
```

## Options

`legacy_tls_warning`
:   A string. The text of the message sent to clients that use outdated
    TLS versions. Default as in the above example.

`legacy_tls_versions`
:   Set of TLS versions, defaults to
    `{ "SSLv3", "TLSv1", "TLSv1.1" }`{.lua}, i.e. TLS \< 1.2.

# Compatibility

  Prosody-Version   Status
  ----------------- ----------------------
  trunk             Works as of 25-05-25
  13                Works
  0.12              Works
