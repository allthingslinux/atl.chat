---
description: HTTP File Upload (external service)
labels:
- Stage-Beta
---

Introduction
============

This module implements [XEP-0363], which lets clients upload files
over HTTP to an external web server.

This module generates URLs that are signed using a HMAC. Any web service that can authenticate
these URLs can be used.

Implementations
---------------

* [PHP implementation](https://hg.prosody.im/prosody-modules/raw-file/tip/mod_http_upload_external/share.php)
* [Python3+Flask implementation](https://github.com/horazont/xmpp-http-upload)
* [Go implementation, Prosody Filer](https://github.com/ThomasLeister/prosody-filer)
* [Perl implementation for nginx](https://github.com/weiss/ngx_http_upload)
* [Rust implementation](https://gitlab.com/nyovaya/xmpp-http-upload)

To implement your own service compatible with this module, check out the implementation notes below
(and if you publish your implementation - let us know!).

Configuration
=============

The module can be added as a new Component definition:

``` {.lua}
Component "upload.example.org" "http_upload_external"
http_upload_external_base_url = "https://your.example.com/upload/service"
http_upload_external_secret = "your shared secret"
```

It should **not** be added to modules_enabled.


External URL
------------

You need to provide the path to the external service. Ensure it ends with '/'.

For example, to use the PHP implementation linked above, you might set it to:

``` {.lua}
http_upload_external_base_url = "https://your.example.com/path/to/share.php/"
```

Secret
------

Set a long and unpredictable string as your secret. This is so the upload service can verify that
the upload comes from mod_http_upload_external, and random strangers can't upload to your server.

``` {.lua}
http_upload_external_secret = "this is a secret string!"
```

You need to set exactly the same secret string in your external service.

Limits
------

A maximum file size can be set by:

``` {.lua}
http_upload_external_file_size_limit = 123 -- bytes
```

Default is 100MB (100\*1024\*1024).

Access
------

You may want to give upload access to additional entities such as components
by using the `http_upload_external_access` config option.

``` {.lua}
http_upload_external_access = {"gateway.example.com"};
```

Compatibility
=============

  Prosody-Version   Status
  ----------------- ----------------------
  trunk             Works as of 25-06-13
  13.0              Works
  0.12              Works

Implementation
==============

To implement your own external service that is compatible with this module, you need to expose a
simple API that allows the HTTP GET, HEAD and PUT methods on arbitrary URLs located on your service.

For example, if http_upload_external_base_url is set to `https://example.com/upload/` then your service
might receive the following requests:

Upload a new file:

```
PUT https://example.com/upload/foo/bar.jpg?v=49e9309ff543ace93d25be90635ba8e9965c4f23fc885b2d86c947a5d59e55b2
```

Recipient checks the file size and other headers:

```
HEAD https://example.com/upload/foo/bar.jpg
```

Recipient downloads the file:

```
GET https://example.com/upload/foo/bar.jpg
```

The only tricky logic is in validation of the PUT request. Firstly, don't overwrite existing files (return 409 Conflict).

Then you need to validate the auth token.

### Validating the auth token


| Version | Supports                                                                                                |
|:--------|:--------------------------------------------------------------------------------------------------------|
| v       | Validates only filename and size. Does not support file type restrictions by the XMPP server.           |
| v2      | Validates the filename, size and MIME type. This allows the server to implement MIME type restrictions. |

It is probable that a future v3 will be specified that allows carrying information about the uploader identity, allowing
the implementation of per-user quotas and limits.

Implementations may implement one or more versions of the protocol simultaneously. The XMPP server generates the URLs and
ultimately selects which version will be used.

XMPP servers MUST only generate URLs with **one** of the versions listed here. However in case multiple parameters are
present, upload services MUST **only** use the token from the highest parameter version that they support.

#### Version 1 (v)

The token will be in the URL query parameter 'v'. If it is absent, fail with 403 Forbidden.

Calculate the expected auth token by reading the value of the Content-Length header of the PUT request. E.g. for a 1MB file
will have a Content-Length of '1048576'. Append this to the uploaded file name, separated by a space (0x20) character.

For the above example, you would end up with the following string: "foo/bar.jpg 1048576"

The auth token is a SHA256 HMAC of this string, using the configured secret as the key. E.g.

```
calculated_auth_token = hmac_sha256("foo/bar.jpg 1048576", "secret string")
```

If this is not equal to the 'v' parameter provided in the upload URL, reject the upload with 403 Forbidden.

**Security note:** When comparing `calculated_auth_token` with the token provided in the URL, you must use a constant-time string
comparison, otherwise an attacker may be able to discover your secret key. Most languages/environments provide such a function, such
as `hash_equals()` in PHP, `hmac.compare_digest()` in Python, or `ConstantTimeCompare()` from `crypto/subtle` in Go.

#### Version 2 (v2)

The token will be in the URL query parameter 'v2'. If it is absent, fail with 403 Forbidden.

| Input           | Example     |Read from                                                            |
|:----------------|:------------|:--------------------------------------------------------------------|
|`file_path`      | foo/bar.jpg | The URL of the PUT request, with the service's base prefix removed. |
|`content_length` | 1048576     | Content-Length header                                               |
|`content_type`   | image/jpeg  | Content-Type header                                                 |

The parameters should be joined into a single string, separated by NUL bytes (`\0`):

```
  signed_string = ( file_path + '\0' + content_length + '\0' + content_type )
```

```
  signed_string = "foo/bar.jpg\01048576\0image/jpeg"
```

The expected auth token is the SHA256 HMAC of this string, using the configured secret key as the key. E.g.:

```
calculated_auth_token = hmac_sha256(signed_string, "secret string")
```

If this is not equal to the 'v2' parameter provided in the upload URL, reject the upload with 403 Forbidden.

**Security note:** When comparing `calculated_auth_token` with the token provided in the URL, you must use a constant-time string
comparison, otherwise an attacker may be able to discover your secret key. Most languages/environments provide such a function, such
as `hash_equals()` in PHP, `hmac.compare_digest()` in Python, or `ConstantTimeCompare()` from `crypto/subtle` in Go.

### Security considerations

#### HTTPS

All uploads and downloads should only be over HTTPS. The security of the served content is protected only
by the uniqueness present in the URLs themselves, and not using HTTPS may leak the URLs and contents to third-parties.

Implementations should consider including HSTS and HPKP headers, with consent of the administrator.

#### MIME types

If the upload Content-Type header matches any of the following MIME types, it MUST be preserved and included in the Content-Type
of any GET requests made to download the file:

- `image/*`
- `video/*`
- `audio/*`
- `text/plain`

It is recommended that other MIME types are preserved, but served with the addition of the following header:

```
Content-Disposition: attachment
```

This prevents the browser interpreting scripts and other resources that may potentially be malicious.

Some browsers may also benefit from explicitly telling them not to try guessing the type of a file:

```
X-Content-Type-Options: nosniff
```

#### Security headers

The following headers should be included to provide additional sandboxing of resources, considering the uploaded
content is not understood or trusted by the upload service:

```
Content-Security-Policy: default-src 'none'
X-Content-Security-Policy: default-src 'none'
X-WebKit-CSP: default-src 'none'
```
