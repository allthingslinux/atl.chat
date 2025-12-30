---
labels:
summary: 'HTTP access to prosody’s storage mechanism'
...

Introduction
------------

This module gives HTTP access to prosody’s storage mechanism. It uses
normal HTTP verbs and [Basic HTTP
authentication](http://tools.ietf.org/html/rfc2617), so you could call
it RESTful if you like buzzwords.

Syntax
------

To Fetch data, issue a normal GET request

    GET /data[/<host>/<user>]/<store>[/<format>] HTTP/1.1
    Authorization: <base64(authzid:password)>

OR

    PUT|POST /data[/<host>/<user>]/<store> HTTP/1.1
    Content-Type: text/x-lua | application/json

    <data>

These map to `datamanager.method(user, host, store, data)`, where choice
of `method` and its parameters are explained below.

### Verbs

  Verb     Meaning                         datamanager method
  -------- ------------------------------- ---------------------------
  `GET`    Just fetch data                 `load()` or `list_load()`
  `PUT`    Replace all data in the store   `store()`
  `POST`   Append item to the store        `list_append()`

Note: In a `GET` request, if `load()` returns `nil`, `list_load()` will
be tried instead.

### Fields

  Field      Description                                                                                                             Default
  ---------- ----------------------------------------------------------------------------------------------------------------------- ---------------------------------------------------------------------------
  `host`     Which virtual host to access                                                                                            Required. If not set in the path, the domain-part of the authzid is used.
  `user`     Which users storage to access                                                                                           Required. If not set in the path, uses the node part of the authzid.
  `store`    Which storage to access.                                                                                                Required.
  `format`   Which format to serialize to. `json` and `lua` are supported. When uploading data, the `Content-Type` header is used.   `json`
  `data`     The actual data to upload in a `PUT` or `POST` request.                                                                 `nil`

Note: Only admins can change data for users other than themselves.

### Example usage

Here follows some example usage using `curl`.

Get your account details:

    curl http://prosody.local:5280/data/accounts -u user@example.com:secr1t
    {"password":"secr1t"}

Set someones account details:

    curl -X PUT http://prosody.local:5280/data/example.com/user/accounts -u admin@host:r00tp4ssw0rd --header 'Content-Type: application/json' --data-binary '{"password":"changeme"}'

### Client library

-   https://metacpan.org/module/Prosody::Mod::Data::Access

### TODO

-   Use `Accept` header.

Compatibility
=============

  ------- --------------
  trunk   Doesn't work (uses is_admin)
  0.12    Works?
  ------- --------------
