---
labels:
- Stage-Alpha
rockspec:
  build:
    copy_directories:
    - html
summary: OAuth 2.0 Authorization Server API
---

## Introduction

This module implements an [OAuth2](https://oauth.net/2/)/[OpenID Connect
(OIDC)](https://openid.net/connect/) Authorization Server on top of
Prosody's usual internal authentication backend.

OAuth and OIDC are web standards that allow you to provide clients and
third-party applications limited access to your account, without sharing your
password with them.

With this module deployed, software that supports OAuth can obtain
"access tokens" from Prosody which can then be used to connect to XMPP
accounts using the [OAUTHBEARER SASL mechanism][rfc7628] or via non-XMPP
interfaces such as [mod_rest].

Although this module has been around for some time, it has recently been
significantly extended and largely rewritten to support OAuth/OIDC more fully.

As of April 2023, it should be considered **alpha** stage. It works, we have
tested it, but it has not yet seen wider review, testing and deployment. At
this stage we recommend it for experimental and test deployments only. For
specific information, see the [deployment notes section](#deployment-notes)
below.

Known client implementations:

-   [example shell script for mod_rest](https://hg.prosody.im/prosody-modules/file/tip/mod_rest/example/rest.sh)
-   *(we need you!)*

Support for [OAUTHBEARER][rfc7628] has been added to the Lua XMPP
library, [verse](https://code.matthewwild.co.uk/verse).  If you know of
additional implementations, or are motivated to work on one, please let
us know! We'd be happy to help (e.g. by providing a test server).

## Standards support

Notable supported standards:

- [RFC 6749: The OAuth 2.0 Authorization Framework](https://www.rfc-editor.org/rfc/rfc6749)
- [RFC 7009: OAuth 2.0 Token Revocation](https://www.rfc-editor.org/rfc/rfc7009)
- [RFC 7591: OAuth 2.0 Dynamic Client Registration](https://www.rfc-editor.org/rfc/rfc7591.html)
- [RFC 7628: A Set of Simple Authentication and Security Layer (SASL) Mechanisms for OAuth](https://www.rfc-editor.org/rfc/rfc7628)
- [RFC 7636: Proof Key for Code Exchange by OAuth Public Clients](https://www.rfc-editor.org/rfc/rfc7636)
- [RFC 7662: OAuth 2.0 Token Introspection](https://www.rfc-editor.org/rfc/rfc7662)
- [RFC 8628: OAuth 2.0 Device Authorization Grant](https://www.rfc-editor.org/rfc/rfc8628)
- [RFC 9207: OAuth 2.0 Authorization Server Issuer Identification](https://www.rfc-editor.org/rfc/rfc9207.html)
- [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)
- [OpenID Connect Discovery 1.0](https://openid.net/specs/openid-connect-discovery-1_0.html) (_partial, e.g. missing JWKS_)
- [OpenID Connect Dynamic Client Registration 1.0](https://openid.net/specs/openid-connect-registration-1_0.html)

## Configuration

### Interface

The module presents a web page to users to allow them to authenticate when
a client requests access. Built-in pages are provided, but you may also theme
or entirely override them.

This module honours the `site_name` configuration option that is also used by
a number of other modules:

```lua
site_name = "My XMPP Server"
```

To provide custom templates, specify the path to the template directory:

```lua
oauth2_template_path = "/etc/prosody/custom-oauth2-templates"
```

If you know what features your templates use use you can adjust the
`Content-Security-Policy` header to only allow what is needed:

```lua
oauth2_security_policy = "default-src 'self'" -- this is the default
```

For the Resource Owner Password Grant the `username` is expected to be the only
localpart by default.  If the OAuth client includes the domainpart in the
`username` it submits (e.g. user@example.org instead of just user), set this to
`true`. Note that this requires all clients to follow this format.

```lua
oauth2_expect_username_jid = false
```

### Token parameters

The following options configure the lifetime of tokens issued by the module.
The defaults are recommended.

```lua
oauth2_access_token_ttl = 3600 -- one hour
oauth2_refresh_token_ttl = 604800 -- one week
```

### Dynamic client registration

To allow users to connect any compatible software, you should enable dynamic
client registration.

Dynamic client registration can be enabled by configuring a JWT key. Algorithm
defaults to *HS256*, lifetime defaults to forever.

```lua
oauth2_registration_key = "securely generated JWT key here"
oauth2_registration_algorithm = "HS256"
oauth2_registration_ttl = nil -- unlimited by default
```

Registering a client is described in
[RFC7591](https://www.rfc-editor.org/rfc/rfc7591.html).

In addition to the requirements in the RFC, the following requirements
are enforced:

`client_name`
:   **MUST** be present, is shown to users in consent screen.

`client_uri`
:   **MUST** be present and **MUST** be a `https://` URL.

`redirect_uris`

:   **MUST** contain at least one valid URI. Different rules apply
    depending on the value of `application_type`, see below.

`application_type`

:   Optional, defaults to `web`. Determines further restrictions for
    `redirect_uris`. The following values are supported:

    `web` *(default)*
    :   For web clients. With this, `redirect_uris` **MUST** be
        `https://` URIs and **MUST** use the same hostname part as the
        `client_uri`.

    `native`
    :   For native e.g. desktop clients etc. `redirect_uris` **MUST**
        match one of:

        -   Loopback HTTP URI, e.g. `http://127.0.0.1/` or
            `http://[::1]`
        -   Application-specific scheme, e.g. `com.example.app:/`
        -   The special OOB URI `urn:ietf:wg:oauth:2.0:oob`

`tos_uri`, `policy_uri`
:   Informative URLs pointing to Terms of Service and Service Policy
    document **MUST** use the same scheme (i.e. `https://`) and hostname
    as the `client_uri`.

#### Registration Examples

In short registration works by POST-ing a JSON structure describing your
client to an endpoint:

``` bash
curl -sSf https://xmpp.example.net/oauth2/register \
    -H Content-Type:application/json \
    -H Accept:application/json \
    --data '
{
   "client_name" : "My Application",
   "client_uri" : "https://app.example.com/",
   "redirect_uris" : [
      "https://app.example.com/redirect"
   ]
}
'
```

Another example with more fields:

``` bash
curl -sSf https://xmpp.example.net/oauth2/register \
    -H Content-Type:application/json \
    -H Accept:application/json \
    --data '
{
   "application_type" : "native",
   "client_name" : "Desktop Chat App",
   "client_uri" : "https://app.example.org/",
   "contacts" : [
      "support@example.org"
   ],
   "policy_uri" : "https://app.example.org/about/privacy",
   "redirect_uris" : [
      "http://localhost:8080/redirect",
      "org.example.app:/redirect"
   ],
   "scope" : "xmpp",
   "software_id" : "32a0a8f3-4016-5478-905a-c373156eca73",
   "software_version" : "3.4.1",
   "tos_uri" : "https://app.example.org/about/terms"
}
'
```

### Supported flows

-   Authorization Code grant, optionally with Proof Key for Code Exchange
-   Device Authorization Grant
-   Resource owner password grant *(disabled by default)*
-   Implicit flow *(disabled by default)*
-   Refresh Token grants

Various flows can be disabled and enabled with
`allowed_oauth2_grant_types` and `allowed_oauth2_response_types`:

```lua
-- These examples reflect the defaults
allowed_oauth2_grant_types = {
	"authorization_code"; -- authorization code grant
	"device_code";
	-- "password"; -- resource owner password grant disabled by default
}

allowed_oauth2_response_types = {
	"code"; -- authorization code flow
    -- "token"; -- implicit flow disabled by default
}
```

The [Proof Key for Code Exchange][RFC 7636] mitigation method is
required by default but can be made optional:

```lua
oauth2_require_code_challenge = false -- default is true
```

Further, individual challenge methods can be enabled or disabled:

```lua
-- These reflects the default
allowed_oauth2_code_challenge_methods = {
    -- "plain"; -- insecure but backwards-compatible
    "S256";
}
```

### Policy documents

Links to Terms of Service and Service Policy documents can be advertised
for use by OAuth clients:

```lua
oauth2_terms_url = "https://example.com/terms-of-service.html"
oauth2_policy_url = "https://example.com/service-policy.pdf"
-- These are unset by default
```

## Deployment notes

### Access management

This module does not provide an interface for users to manage what they have
granted access to their account! (e.g. to view and revoke clients they have
previously authorized). It is recommended to join this module with
[mod_client_management] to provide such access. However, at the time of writing,
no XMPP clients currently support the protocol used by that module. We plan to
work on additional interfaces in the future.

### Scopes

OAuth supports "scopes" as a way to grant clients limited access.

[XEP-0493: OAuth Client Login] describes using OAuth 2.0 / OpenID Connect with XMPP.
This module does not yet support [the scopes defined](https://xmpp.org/extensions/xep-0493.html#oauth-scopes).
This means that clients you authorize currently have to
choose between unrestricted access to your account (including the
ability to change your password and lock you out!) and zero access. So,
for now, while using OAuth clients can prevent leaking your password to
them, it is not currently suitable for connecting untrusted clients to
your account.

As a first step, the `xmpp` scope is supported, and corresponds to
whatever permissions the user would have when logged in over XMPP.

Further, known Prosody roles can be used as scopes.

OpenID scopes such as `openid` and `profile` can be used for "Login
with XMPP" without granting access to more than limited profile details.

The `offline_access` scope must be requested to receive refresh tokens.

## Compatibility

Requires Prosody trunk (April 2023 or later) or Prosody 13.0,
**not** compatible with Prosody 0.12 or earlier.
