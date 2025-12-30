---
labels:
- 'Stage-Beta'
summary: |
    Stops prosody from including starttls into available features for
    specified remote servers.
...

Details
-------

Let's you stop Prosody from sending \<starttls
xmlns='urn:ietf:params:xml:ns:xmpp-tls'\> feature to choppy/buggy
servers which therefore would fail to re-negotiate and use a secure
stream. (e.g. [OpenFire
3.7.0](http://issues.igniterealtime.org/browse/OF-405))

Usage
-----

Copy the plugin into your prosody's modules directory.

And add it between your enabled modules into the global section
(modules\_enabled).

Then list each host as follow:

    tls_s2s_blacklist = { "host1.tld", "host2.tld", "host3.tld" }

In the unfortunate case of OpenFire... you can add the Server's ip
address directly as it may not send proper rfc6121 requests.

    tls_s2s_blacklist_ip = { "a.a.a.a", "b.b.b.b", "c.c.c.c" }

Compatibility
-------------

It's supposed to work with 0.7-0.8.x
