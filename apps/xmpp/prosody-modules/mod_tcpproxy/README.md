---
labels:
- 'Stage-Beta'
summary: 'TCP-over-XMPP :)'
...

Introduction
============

It happens occasionally that I would like to use the XMPP server as a
generic proxy for connecting to another service. It is especially
awkward in some environments, and impossible in (for example) Javascript
inside a web browser.

Details
=======

Using mod\_tcpproxy an XMPP client (including those using BOSH) can
initiate a pipe to a given TCP/IP address and port. This implementation
uses the [In-Band Bytestreams](http://xmpp.org/extensions/xep-0047.html)
XEP, simply extended with 2 new attributes in a new namespace, host and
port.

An example Javascript client can be found in the web/ directory of
mod\_tcpproxy in the repository.

Configuration
=============

Just add tcpproxy as a component, for example:

`Component "tcp.example.com" "tcpproxy"`

Protocol
========

A new stream is opened like this:

``` {.xml}
<iq type="set" id="newconn1" to="tcp.example.com">
  <open xmlns='http://jabber.org/protocol/ibb'
        sid='connection1'
        block-size='4096'
        stanza='message'
        xmlns:tcp='http://prosody.im/protocol/tcpproxy'
        tcp:host='example.com'
        tcp:port='80' />
</iq>
```

The stanza attribute (currently) MUST be 'message', and block-size is
(currently) ignored.

In response to this stanza you will receive a result upon connection
success, or an error if the connection failed. You can then send to the
connection by sending message stanzas as described in the IBB XEP.
Incoming data will likewise be delivered as messages.

Compatibility
=============

  ----- --------------
  0.7   Works
  0.6   Doesn't work
  ----- --------------

Todo
====

-   ACLs (restrict to certain JIDs, and/or certain target hosts/ports)
-   Honour block-size
-   Support iq stanzas for data transmission
-   Signal to start SSL/TLS on a connection
