---
summary: OIDC UserInfo profile details from vcard4
labels:
- Stage-Alpha
rockspec:
  dependencies:
  - mod_http_oauth2 >= 200
---

This module extracts profile details from the user's [vcard4][XEP-0292]
and provides them in the [UserInfo] endpoint of [mod_http_oauth2] to
clients the user grants authorization.

Whether this is really needed is unclear at this point. When logging in
with an XMPP client, it could fetch the actual vcard4 to retrieve these
details, so the UserInfo details would probably primarily be useful to
other OAuth 2 and OIDC clients.

[UserInfo]: https://openid.net/specs/openid-connect-core-1_0.html#UserInfoResponse
