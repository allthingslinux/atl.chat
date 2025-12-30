---
labels:
- 'Stage-Stable'
summary: 'Token based JSON registration & verification servlet.'
...

Introduction
------------

This module let's you activate a httpserver interface to handle data
from webforms with POST and Base64 encoded JSON.

Implementation Details
----------------------

Example Request format:

    POST /your_register_base_url HTTP/1.1
    Host: yourserveraddress.com:yourchoosenport
    Content-Type: application/encoded
    Content-Transfer-Encoding: base64

    eyJ1c2VybmFtZSI6InVzZXJuYW1lb2ZjaG9pY2UiLCJwYXNzd29yZCI6InRoZXVzZXJwYXNzd29yZCIsImlwIjoidGhlcmVtb3RlYWRkcm9mdGhldXNlciIsIm1haWwiOiJ1c2VybWFpbEB1c2VybWFpbGRvbWFpbi50bGQiLCJhdXRoX3Rva2VuIjoieW91cmF1dGh0b2tlbm9mY2hvaWNlIn0=

Where the encoded content is this (example) JSON Array:

``` {.json}
    {
      "username":"john.smith",
      "password":"secret-password",
      "ip":"192.168.0.0",
      "mail":"john.smith@mail.example.net",
      "auth_token":"yourauthtokenofchoice"
    }
```

Your form implementation needs to pass **all** parameters, the
auth\_token is needed to prevent misuses, if the request is successful
the server will answer with status code 200 and with the body of the
response containing the token which your web app can send via e-mail to
the user to complete the registration.

Else, it will reply with the following http error codes:

-   400 - if there's an error syntax;
-   401 - whenever an username is already pending registration or the
    auth token supplied is invalid;
-   403 - whenever registration is forbidden (blacklist, filtered mail
    etc.);
-   406 - if the username supplied fails nodeprepping;
-   409 - if the user already exists, or an user is associated already
    with the supplied e-mail;
-   503 - whenever a request is throttled.

The verification URL path to direct the users to will be:
**/your-base-path-of-choice/verify/** - on your Prosody's http server.

The module for now stores a hash of the user's mail address to help slow
down duplicated registrations.

It's strongly encouraged to have the web server communicate with the
servlet via https.

Usage
-----

Copy the module folder and all its contents (register\_json) into your
prosody modules' directory.Add the module your vhost of choice
modules\_enabled.

Hint: pairing with mod\_register\_redirect is helpful, to allow server
registrations only via your webform.


Required configuration:

```
    reg_servlet_auth_token = "your-secret-token"
```

Optional configuration directives:

```
    reg_servlet_base = "/base-path/" -- Base path of the plugin (default is register_account)
    reg_servlet_secure = true -- Have the plugin only process requests on https (default is true)
    reg_servlet_ttime = seconds -- Specifies the time (in seconds) between each request coming from the same remote address.
    reg_servlet_bl = { "1.2.3.4", "4.3.2.1" } -- The ip addresses in this list will be blacklisted and will not be able to submit registrations.
    reg_servlet_wl = { "1.2.3.4", "4.3.2.1" } -- The ip addresses in this list will be ignored by the throttling.
    reg_servlet_filtered_mails = { ".*banneddomain.tld", ".*deamailprovider.tld" } -- allows filtering of mail addresses via Lua patterns.
```

Compatibility
-------------

0.9
