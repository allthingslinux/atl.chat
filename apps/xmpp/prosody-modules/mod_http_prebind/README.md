---
labels:
- 'Stage-Alpha'
summary: Implements BOSH pre-bind
...

For why this can be useful, see
https://metajack.im/2009/12/14/fastest-xmpp-sessions-with-http-prebinding/

# To enable this module

Add `"http_prebind"` to `modules_enabled` on an anonymous virtual host.

This only works on anonymous ones for now.
