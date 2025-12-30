---
summary: HTTP Authentication using custom JSON protocol
...

Introduction
============

To authenticate users, this module does a `POST` request to a configured
URL with a JSON payload. It is not async so requests block the server
until answered.

Configuration
=============

``` lua
VirtualHost "example.com"
authentication = "custom_http"
auth_custom_http = {
  post_url = "http://api.example.com/auth";
}
```

Protocol
========

The JSON payload consists of an object with `username` and `password`
members:

    {"username":"john","password":"secr1t"}

The module expects the response body to be exactly `true` if the
username and password are correct.
