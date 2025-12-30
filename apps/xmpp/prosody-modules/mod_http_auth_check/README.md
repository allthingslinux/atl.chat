---
labels:
summary: 'Test account credentials using HTTP'
...

Introduction
------------

This module lets you test whether a set of credentials are valid,
using Prosody's configured authentication mechanism.

This is useful as an easy way to allow other (e.g. non-XMPP) applications
to authenticate users using their XMPP credentials.

Syntax
------

To test credentials, issue a simple GET request with HTTP basic auth:

    GET /auth_check HTTP/1.1
    Authorization: Basic <base64(jid:password)>

Prosody will return a 2xx code on success (user exists and credentials are
correct), or 401 if the credentials are invalid. Any other code may be returned
if there is a problem handling the request.

### Example usage

Here follows some example usage using `curl`.

    curl http://prosody.local:5280/auth_check -u user@example.com:secr1t
