---
labels:
- Stage-Alpha
...

Introduction
============

This is an experimental authentication module that does an asynchronous
HTTP call to verify username and password.

This is a (possibly temporary) fork of mod_http_auth_async that adds
support for authentication using a cookie and SASL EXTERNAL.

Details
=======

When a user attempts to authenticate to Prosody, this module takes the
username and password and does a HTTP GET request with [Basic
authentication][rfc7617] to the configured `http_auth_url`.

Configuration
=============

``` lua
VirtualHost "example.com"
  authentication = "http_auth_cookie"
  http_auth_url = "http://example.com/auth"
  http_cookie_auth_url = "https://example.com/testcookie.php?user=$user"
```

Cookie Authentication
=====================

It is possible to link authentication to an existing web application. This
has the benefit that the user logging into the web application in their
browser will automatically log them into their XMPP account.

There are some prerequisites for this to work:

  - The BOSH or Websocket requests must include the application's cookie in
  the headers sent to Prosody. This typically means the web chat code needs
  to be served from the same domain as the web application.
  
  - The web application must have a URL that returns 200 OK when called with
  a valid cookie, and returns a different status code if the cookie is invalid
  or not currently logged in.
  
  - The XMPP username for the user must be passed to Prosody by the client, or
  returned in the 200 response from the web application.

Set `http_cookie_auth_url` to the web application URL that is used to check the
cookie. You may use the variables `$host` for the XMPP host and `$user` for the
XMPP username.

If the `$user` variable is included in the URL, the client must provide the username
via the "authzid" in the SASL EXTERNAL authentication mechanism.

If the `$user` variable is *not* included in the URL, Prosody expects the web application's response to be the username instead, as UTF-8 text/plain.

Compatibility
=============

Requires Prosody trunk
