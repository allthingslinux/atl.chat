---
summary: Allow server administrators to probe any user
...

This module lets server administrators send `<presence type="probe"/>`
to any local user and receive their presence in response, bypassing
roster checks.

Compatibility
=============

  ------- --------------
  trunk   Doesn't work (uses is_admin)
  0.12    Works?
  ------- --------------
