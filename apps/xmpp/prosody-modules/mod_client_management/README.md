---
labels:
- Stage-Beta
summary: "Manage clients with access to your account"
rockspec:
  dependencies:
  - mod_sasl2_fast
---

This module allows a user to identify what currently has access to their
account.

This module depends on [mod_sasl2_fast] and mod_tokenauth (bundled with
Prosody). Both will be automatically loaded if this module is loaded.

## Configuration

| Name                      | Description                                            | Default         |
|---------------------------|--------------------------------------------------------|-----------------|
| enforce_client_ids        | Only allow SASL2-compatible clients                    | `false`         |

When `enforce_client_ids` is not enabled, the client listing may be less accurate due to legacy clients,
which can only be tracked by their resource, which is public information, not necessarily unique to a
client instance, and is also exposed to other XMPP entities the user communicates with.

When `enforce_client_ids` is enabled, clients that don't support SASL2 and provide a client id will be
denied access.

## Shell usage

You can use this module via the Prosody shell. For example, to list a user's
clients:

```shell
prosodyctl shell user clients user@example.com
```

To revoke access from particular client:

```shell
prosodyctl shell user revoke_client user@example.com grant/xxxxx
```

## Compatibility

Requires Prosody 13.0.
Not compatible with Prosody 0.12 and earlier.

## Developers

### Protocol

#### Listing clients

To list clients that have access to the user's account, send the following
stanza:

```xml
<iq id="p" type="get">
  <list xmlns="xmpp:prosody.im/protocol/manage-clients"/>
</iq>
```

The server will respond with a list of clients:

```xml
<iq id="p" to="mattj-gajim@auth2.superxmpp.com/gajim.UYJKBHKT" type="result" xmlns="jabber:client">
  <clients xmlns="xmpp:prosody.im/protocol/manage-clients">
    <client connected="true" id="client/zeiP41HLglIu" type="session">
      <first-seen>2023-04-06T14:26:08Z</first-seen>
      <last-seen>2023-04-06T14:37:25Z</last-seen>
      <auth>
        <password/>
      </auth>
      <user-agent>
        <software>Gajim</software>
        <uri>https://gajim.org/</uri>
        <device>Juliet's laptop</device>
      </user-agent>
    </client>
    <client connected="false" id="grant/HjEEr45_LQr" type="access">
      <first-seen>2023-03-27T15:16:09Z</first-seen>
      <last-seen>2023-03-27T15:37:24Z</last-seen>
      <user-agent>
        <software>REST client</software>
      </user-agent>
    </client>
  </clients>
</iq>
```

On the `<client/>` tag most things are self-explanatory. The following attributes
are defined:

- 'connected': a boolean that reflects whether this client has an active session
on the server (i.e. this includes connected and "hibernating" sessions).
- 'id': an opaque reference for the client, which can be used to revoke access.
- 'type': either `"session"` if this client is known to have an active or inactive
  client session on the server, or "access" if no session has been established (e.g.
  it may have been granted access to the account, but only used non-XMPP APIs or
  never logged in).

The `<first-seen/>` and `<last-seen/>` elements contain timestamps that reflect
when a client was first granted access to the user's account, and when it most
recently used that access. For active sessions, it may reflect the current
time or the time of the last login.

The `<user-agent/>` element contains information about the client software. It
may contain any of three optional child elements, each containing text content:

- `<software/>` - the name of the software
- `<uri/>` - a URI/URL for the client, such as a homepage
- `<device/>` - a human-readable identifier/name for the device where the client
  runs

The `<auth/>` element lists the known authentication methods that the client
has used to gain access to the account. The following elements are defined:

- `<password/>` - the client has presented a valid password
- `<grant/>` - the client has a valid authorization grant (e.g. via OAuth)
- `<fast/>` - the client has active FAST tokens

#### Revoking access

To revoke a client's access, send a `<revoke/>` element with an 'id' attribute
containing one of the client ids fetched from the list:

```xml
<iq id="p" type="set">
  <revoke xmlns="xmpp:prosody.im/protocol/manage-clients" id="grant/HjEEr45_LQr" />
</iq>
```

The server will respond with an empty result if the revocation succeeds:

```xml
<iq id="p" type="result" />
```

If the client has previously authenticated with a password, there is no way to
revoke access except by changing the user's password. If you request
revocation of such a client, the server will respond with a 'service-unavailable'
error, with the 'password-reset-required' application error:

```xml
<iq id="p" type="error">
  <error type="cancel">
    <service-unavailable xmlns="xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'">
    <password-reset-required xmlns="xmpp:prosody.im/protocol/manage-clients"/>
  </error>
</iq>
```
