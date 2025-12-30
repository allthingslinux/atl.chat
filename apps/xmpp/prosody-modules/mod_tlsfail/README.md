---
summary: STARTTLS failure test
---

This module responds to `<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>` with
`<failure xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>`, in order to test
how clients and server behave.

See [RFC6120 Section 5.4.2.2](https://xmpp.org/rfcs/rfc6120.html#rfc.section.5.4.2.2)

