---
summary: OIDC group membership in UserInfo
labels:
- Stage-Alpha
rockspec:
  dependencies:
  - mod_http_oauth2 >= 200
  - mod_groups_internal
---

This module exposes [mod_groups_internal] groups to
[OAuth 2.0][mod_http_oauth2] clients via a `groups` scope/claim.
