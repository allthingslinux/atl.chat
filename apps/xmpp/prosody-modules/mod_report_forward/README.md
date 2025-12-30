---
labels:
- 'Stage-Beta'
summary: 'Forward spam/abuse reports to a JID'
---

This module forwards spam/abuse reports (e.g. those submitted by users via
XEP-0377 via mod_spam_reporting) to one or more JIDs.

## Configuration

Install and enable the module the same as any other:

```lua
modules_enabled = {
    ---
    "report_forward";
    ---
}
```

There are two main options. You can set `report_forward_to` which accepts a
list of JIDs to send all reports to (default is empty):

```lua
report_forward_to = { "admin@example.net", "antispam.example2.com" }
```

You can also control whether the module sends a report to the server from
which the spam/abuse originated (default is `true`):

```lua
report_forward_to_origin = false
```

The module looks up an abuse report address using XEP-0157 (only XMPP
addresses are accepted). If it fails to find any suitable destination, it will
fall back to sending the report to the domain itself unless `report_forward_to_origin_fallback`
is disabled (set to `false`). If the fallback is disabled, it will log a
warning and not send the report.



## Protocol

This section is intended for developers.

XEP-0377 assumes the report is embedded within another protocol such as
XEP-0191, and doesn't specify a format for communicating "standalone" reports.
This module transmits them inside a `<message>` stanza, and adds a `<jid/>`
element (borrowed from XEP-0268):

```xml
<message from="prosody.example" to="destination.example">
    <report xmlns="urn:xmpp:reporting:1" reason="urn:xmpp:reporting:spam">
        <jid xmlns="urn:xmpp:jid:0">spammer@bad.example</jid>
        <text>
          Never came trouble to my house like this.
        </text>
    </report>
</message>
```

It may also include the reported message, if this has been indicated by the
user, wrapped in a XEP-0297 `<forwarded/>` element:

```xml
<message from="prosody.example" to="destination.example">
  <report reason="urn:xmpp:reporting:spam" xmlns="urn:xmpp:reporting:1">
    <jid xmlns="urn:xmpp:jid:0">spammer@bad.example</jid>
    <text>Never came trouble to my house like this.</text>
  </report>
  <forwarded xmlns="urn:xmpp:forward:0">
    <message from="spammer@bad.example" to="victim@prosody.example" type="chat" xmlns="jabber:client">
      <body>Spam, Spam, Spam, Spam, Spam, Spam, baked beans, Spam, Spam and Spam!</body>
    </message>
  </forwarded>
</message>
```

## Compability

  Prosody-Version   Status
  ----------------- ----------------------
  trunk             Works as of 07.12.22
  0.12              Works
