---
summary: Authenticate against an external OAuth 2 IdP
labels:
- Stage-Alpha
---

This module provides external authentication via an external [OAuth
2](https://datatracker.ietf.org/doc/html/rfc7628) authorization server
and supports the [SASL OAUTHBEARER authentication][rfc7628]
mechanism as well as PLAIN for legacy clients (this is all of them).

# How it works

Using OAuth 2.0 in XMPP is explained in [XEP-0493: OAuth Client Login].
Clients pass tokens from the Authorization Server to Prosody, which
attempts to validate the tokens using the configured validation
endpoint.

Legacy clients have to use SASL PLAIN, where Prosody receives the users
username and password and attempts to validate this using the OAuth 2
resource owner password grant.

# Configuration

## Example

```lua
-- authentication = "oauth_external"

oauth_external_discovery_url = "https//auth.example.com/auth/realms/TheRealm/.well-known/openid-configuration"
oauth_external_token_endpoint = "https//auth.example.com/auth/realms/TheRealm/protocol/openid-connect/token"
oauth_external_validation_endpoint = "https//auth.example.com/auth/realms/TheRealm/protocol/openid-connect/userinfo"
oauth_external_username_field = "xmpp_username"
```


## Common

`oauth_external_issuer`
:   Optional URL string representing the Authorization server identity.

`oauth_external_discovery_url`
:   Optional URL string pointing to [OAuth 2.0 Authorization Server
    Metadata](https://oauth.net/2/authorization-server-metadata/). Lets
    clients discover where they should retrieve access tokens from if
    they don't have one yet. Default based on `oauth_external_issuer` is
    set, otherwise empty.

`oauth_external_validation_endpoint`
:   URL string. The token validation endpoint, should validate the token
    and return a JSON structure containing the username of the user
    logging in the field specified by `oauth_external_username_field`.
    Commonly the [OpenID `UserInfo`
    endpoint](https://openid.net/specs/openid-connect-core-1_0.html#UserInfo)
    If left unset, only `SASL PLAIN` is supported and the username
    provided there is assumed correct.

`oauth_external_username_field`
:   String. Default is `"preferred_username"`. Field in the JSON
    structure returned by the validation endpoint that contains the XMPP
    localpart.

## For SASL PLAIN

`oauth_external_resource_owner_password`
:   Boolean. Defaults to `true`. Whether to allow the *insecure*
    [resource owner password
    grant](https://oauth.net/2/grant-types/password/) and SASL PLAIN.

`oauth_external_token_endpoint`
:   URL string. OAuth 2 [Token
    Endpoint](https://www.rfc-editor.org/rfc/rfc6749#section-3.2) used
    to retrieve token in order to then retrieve the username.

`oauth_external_client_id`
:   String. Client ID used to identify Prosody during the resource owner
    password grant.

`oauth_external_client_secret`
:   String. Client secret used to identify Prosody during the resource
    owner password grant.

`oauth_external_scope`
:   String. Defaults to `"openid"`. Included in request for resource
    owner password grant.

# Compatibility

## Prosody

  Version   Status
  --------- -----------------------------------------------
  trunk     works
  0.12.x    OAUTHBEARER will not work, otherwise untested
  0.11.x    OAUTHBEARER will not work, otherwise untested

## Identity Provider

Tested with

-   [KeyCloak](https://www.keycloak.org/)
-   [Mastodon](https://joinmastodon.org/)

# Future work

-   Automatically discover endpoints from Discovery URL
-   Configurable input username mapping (e.g. user → user@host).
-   [SCRAM over HTTP?!][rfc7804]
