# Push 2.0

Adapted from notes made at [XMPP Summit 25](https://pad.nixnet.services/oy6MKVbESSycLeMJIOh6zw).

Requirements:

- Support for SASL2 inlining
- Extensible stanza matching rules and notification payload rules
- Simpler syntax and concept model than original specification

## Client registers to receive push notifications

```xml
<enable xmlns='urn:xmpp:push2:0'>
    <service>pusher@push.example.com</service>
    <client>https://push.example.com/adlfkjadafdasf</client>
    <match profile="urn:xmpp:push2:match:archived-with-body">
        <grace>144</grace>
        <filter jid="somemuc@conference.example.com">
            <mention/>
        </filter>
        <send xmlns="urn:xmpp:push2:send:notify-only:0"/>
    </match>
</enable>
```

The `<service/>` element contains a JID which push notifications for this client will be sent to. It may be a host, bare or full JID.

The `<client/>` element contains an opaque string that will be included in all communication with the push service. It may be used to convey client identifiers used by the push notification service to route notifications.

The `<match/>` and `<send/>` elements define what profiles to use for matching stanzas and sending notifications. These are described later in this document.

The optional `<filter/>` child of `<match/>` allows extra filtering of pushes for only specific chats. No specified filters means muted, do not push. `<mention/>` means push on mentions, `<reply/>` means push on replies.

The optional `<grace/>` child of `<match/>` allows specifying a "grace period" in seconds where activity on another session by the same user (such as sending a message) will temporarily pause sending push notifications.

## Match and send profiles

Different clients and push services have different requirements for push notifications, often due to the differing capabilities of target platforms.

A "profile" in the context of this specification is a set of rules for matching the kinds of stanzas that should be pushed, and how to transform them before sending the notification to the push service.

### Match profiles

Match profiles define which incoming stanzas will trigger a push notification. More than one match may be specified.

Some match profiles are defined in this XEP. Other XEPs may define additional profiles with the reserved `urn:xmpp:push2:match:` prefix, following the registrar considerations explained later in this document. Custom profiles not defined in a XEP should use their own appropriate URI.

#### `urn:xmpp:push2:match:all`

Using this profile, all stanzas will trigger a push notification to be sent to the push service when the client is unavailable.

#### `urn:xmpp:push2:match:important`

Stanzas that are considered to be "important" are pushed. At the time of writing, there is no standard definition of "important", however most servers already contain such logic for traffic optimization when combined with [XEP-0352: Client State Indication](https://xmpp.org/extensions/xep-0352.html).

#### `urn:xmpp:push2:match:archived`

Push notifications will be sent for any stanza that is stored in the user's archive. This is a good indication that the stanza is important, and is desired on all of a user's devices.

#### `urn:xmpp:push2:match:archived-with-body`

Matches only archived messages that contain a body. This can be used to exclude certain message types, such as typing notifications, receipts and error replies.

### Send profiles

When a server has determined that a stanza should trigger a push notification (according to the client's selected 'match' profile), it proceeds to create a notification stanza following the send profiles specified in the match profiles which match this stanza.

After constructing the notification stanza, it will then be sent to the push service JID selected by the client.

Some send profiles are defined in this XEP. Other XEPs may define additional profiles with the `urn:xmpp:push2:send:` prefix, following the registrar considerations explained later in this document. Custom profiles not defined in a XEP should use their own appropriate URI.

#### `urn:xmpp:push2:send:notify-only:0`

Send an empty notification to the push service. Such notifications are useful if a push notification can trigger the client to "wake up" and connect to the server to receive the message over XMPP.

Example:

```xml
<message to="pusher@push.example.net">
    <notification xmlns="urn:xmpp:push2:0">
        <client>https://push.example.com/adlfkjadafdasf</client>
        <priority>normal</priority>
    </notification>
</message>
```

#### `urn:xmpp:push2:send:sce+rfc8291+rfc8292:0`

Delivers content encrypted according to RFC8291 and with a JWT auth following RFC8292

```xml
<send xmlns="urn:xmpp:push2:send:sce+rfc8291+rfc8292:0">
    <ua-public>Base64 encoded P-256 ECDH public key (raw, uncompressed)</ua-public>
    <auth-secret>Base64 encoded randomly generated 16 octets</auth-secret>
    <jwt-alg>ES256</jwt-alg>
    <jwt-key>PKCS#8 PEM encoded ECDSA keypair, without the header or footer lines</jwt-key>
    <jwt-claim name="aud">https://push.example.com</jwt-claim>
</send>
```

The full stanza is wrapped in XEP-0297 forwarded and then that is wrapped in XEP-0420 envelope/content with optional rpad. The raw bytes of the resulting XML are encrypted according to RFC8291 using the provided `ua-public` and `auth-secret`.

If `jwt-alg` is specified, then a JWT is computed over any provided claims plus a suitable `exp` and `sub` claim and signed using the provided key.

Then a notification is sent:

```xml
<message to="pusher@push.example.net">
    <notification xmlns="urn:xmpp:push2:0">
        <client>https://push.example.com/adlfkjadafdasf</client>
        <priority>normal</priority>
        <encrypted xmlns="urn:xmpp:sce:rfc8291:0">
            <payload>Base64 encoded ciphertext</payload>
        </encrypted>
        <jwt key="base64 encoded raw public key">the signed JWT, if present</jwt>
    </notification>
</message>
```

NOTE: if the stanza exceeds the maximum size of 4096 bytes (and some implementations may wish to restrict this even more) the stanza may have some elements removed, body truncated, etc before it is delivered. Servers SHOULD ensure that at least the MAM id (if there is one) is still present after any minimization.

## Discovering support

A server that supports this protocol MUST advertise the `urn:xmpp:push2:0` feature in an account's service discovery information, along with the supported match and send profiles.

```xml
<iq from='juliet@capulet.lit'
    to='juliet@capulet.lit/balcony'
    id='disco1'
    type='result'>
  <query xmlns='http://jabber.org/protocol/disco#info'>
    <identity category='account' type='registered'/>
    <feature var='urn:xmpp:push2:0'/>
    <feature var='urn:xmpp:push2:send:'/>
  </query>
</iq>
```

## Client disables future pushes

```xml
<disable xmlns='urn:xmpp:push2:0' />
```

## Push service interactions

### Transient delivery errors

The user's server might receive delivery errors while sending notifications to the user's push service. The error 'type' attribute SHOULD be honoured - errors of type 'wait' SHOULD be retried in an appropriate manner (e.g. using exponential back-off algorithm, up to a limit), discarding the notification after an appropriate length of time or number of attempts.

Other error types MUST NOT be automatically retried.

A user's server MAY automatically disable a push configuration for a service that has consistently failed to relay notifications for an extended period of time. This period is a matter of deployment configuration, but a default no less than 72 hours is recommended.
