---
labels:
- 'Stage-Beta'
summary: 'Authenticated HTTP API to create invites'
...

Introduction
============

This module is part of the suite of modules that implement invite-based
account registration for Prosody. The other modules are:

- [mod_invites]
- [mod_invites_adhoc]
- [mod_invites_page]
- [mod_invites_register]
- [mod_invites_register_web]
- [mod_register_apps]

For details and a full overview, start with the [mod_invites] documentation.

Details
=======

mod_invites_api provides an authenticated HTTP API to create invites
using mod_invites.

You can use the command-line to create and manage API keys.

Configuration
=============

There are no specific configuration options for this module.

All the usual [HTTP configuration options](https://prosody.im/doc/http)
can be used to configure this module.

API usage
=========

Step 1: Create an API key, with an optional name to help you remember what
it is for

```
$ prosodyctl mod_invites_api create example.com "My test key"
```

**Tip:** Remember to put quotes around your key name if it contains spaces.

The command will print out a key:

```
HTwALnKL/73UUylA-2ZJbu9x1XMATuIbjWpip8ow1
```

Step 2: Make a HTTP request to Prosody, containing the key

```
$ curl -v https://example.com:5281/invites_api?key=HTwALnKL/73UUylA-2ZJbu9x1XMATuIbjWpip8ow1
```

Prosody will respond with a HTTP status code "201 Created" to indicate
creation of the invite, and per HTTP's usual rules, the URL of the created
invite page will be in the `Location` header:

```
< HTTP/1.1 201 Created
< Access-Control-Max-Age: 7200
< Connection: Keep-Alive
< Access-Control-Allow-Origin: *
< Date: Sun, 13 Sep 2020 09:50:19 GMT
< Access-Control-Allow-Headers: Content-Type
< Access-Control-Allow-Methods: OPTIONS, GET
< Content-Length: 0
< Location: https://example.com/invite?c-vhJjyB5Pb4HpAf
```

Sometimes for convenience, you may want to just visit the URL in the
browser. Append `&redirect=true` to the URL, and instead Prosody will
return a `303 See Other` response code, which will tell the browser to
redirect straight to the newly-created invite. This is super handy in a
bookmark :)

If using the API programmatically, it is recommended to put the key in
the `Authorization` header if possible. This is quite simple:

```
Authorization: Bearer HTwALnKL/73UUylA-2ZJbu9x1XMATuIbjWpip8ow1
```

Key management
==============

At any time you can view authorized keys using:

```
prosodyctl mod_invites_api list example.com
```

This will list out the id of each key, and the name if set:

```
HTwALnKL	My test key
```

You can revoke a key by passing this key id to the 'delete` sub-command:

```
prosodyctl mod_invites_api delete example.com HTwALnKL
```