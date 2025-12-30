---
labels:
- 'Stage-Alpha'
summary: 'Proxy multiple client resources behind a single component'
...

What it does
============

This module must be used as a component. For example:

    Component "proxy.domain.example" "client_proxy"
        target_address = "some-user@some-domain.example"

All IQ requests against the proxy host (in the above example:
proxy.domain.example) are sent to a random resource of the target address (in
the above example: some-user@some-domain.example). The entity behind the
target address is called the "implementing client".

The IQ requests are JAT-ed (JAT: Jabber Address Translation) so that when the
implementing client answers the IQ request, it is sent back to the component,
which reverts the translation and routes the reply back to the user.

Let us assume that user@some-domain.example sends a request. The
proxy.domain.example component has the client_proxy module loaded and proxies to
some-user@some-domain.example. some-user@some-domain.example has two resources,
/a and /b.

    user -> component:
        <iq type='get' id='1234' to='proxy.domain.example' from='user@some-domain.example/abc'>
    component -> implementing client:
        <iq type='get' id='1234' to='some-user@some-domain.example/a' from='proxy.domain.example/encoded-from'>
    implementing client -> component:
        <iq type='result' id='1234' to='proxy.domain.example/encoded-from' from='some-user@some-domain.example/a'>
    component -> user:
        <iq type='result' id='1234' to='user@some-domain.example/abc' from='proxy.domain.example'>

The encoded-from resource used in the exchange between the proxy component
and the implementing client is an implementation-defined string which allows
the proxy component to revert the JAT.


Use cases
=========

* Implementation of services within clients instead of components, thus making
  use of the more advanced authentication features.
* Load-balancing requests to different client resources.
* General evilness


Configuration
=============

To use this module, it needs to be loaded on a component:

    Component "proxy.yourdomain.example" "client_proxy"
        target_address = "implementation@yourdomain.example"

It will then send a subscription request to implementation@yourdomain.example
which MUST be accepted: this is required so that the component can detect the
resources to which IQ requests can be dispatched.


Limitations
===========

* It does not handle presence or message stanzas.
* It does not allow the implementing client to initiate IQ requests
