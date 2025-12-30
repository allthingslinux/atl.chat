---
summary: 'Receives HTTP POST request, parses it and relays it into XMPP.'
---

Introduction
============

Sometimes it's useful to have different interfaces to access XMPP.

This module allows sending XMPP
[`<message>`](https://xmpp.org/rfcs/rfc6121.html#message) stanzas via a
simple HTTP API.

Example usage
-------------

    curl http://example.com:5280/msg/user -u me@example.com:mypassword -H "Content-Type: text/plain" -d "Server@host has just crashed!"

This would send a message to user\@example.com from me\@example.com

Details
=======

URL format
----------

    /msg/ [recipient [@host] ].

The base URL defaults to `/msg`. This can be configured via Prosodys
[HTTP path settings][doc:http].

Authentication
--------------

Authentication is done by [HTTP Basic](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Authentication).

    Authorization: Basic BASE64( "username@virtualhost:password" )

Payload formats
---------------

Supported formats are:

`text/plain`
:   The HTTP body is used as plain text message payload, in the `<body>`
    element.

`application/x-www-form-urlencoded`
:   Allows more fields to be specified.

`application/json`
:   Similar to form data.

Which one is selected via the `Content-Type` HTTP header.

### Data fields

The form data and JSON formats allow the following fields:

`to`
:   Can be used instead of having the receiver in the URL.

`type`
:   [Message type.](https://xmpp.org/rfcs/rfc6121.html#message-syntax-type)

`body`
:   Plain text message payload which goes in the `<body>` element.

Acknowledgements
================

Some code originally borrowed from mod\_webpresence

See also
========

[mod_rest] is a more advanced way to send messages and more via HTTP,
with a very similar API.

