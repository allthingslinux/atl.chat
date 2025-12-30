---
labels:
- 'Stage-Beta'
summary: 'MQTT interface to Prosody''s pubsub'
...

Introduction
------------

[MQTT](http://mqtt.org/) is a lightweight binary pubsub protocol suited
to embedded devices. This module provides a way for MQTT clients to
connect to Prosody and publish or subscribe to local pubsub nodes.

The module currently implements MQTT version 3.1.1.

Details
-------

MQTT has the concept of 'topics' (similar to XMPP's pubsub 'nodes').
mod\_pubsub\_mqtt maps pubsub nodes to MQTT topics of the form
`<HOST>/<TYPE>/<NODE>`, e.g.`pubsub.example.org/json/mynode`.

The 'TYPE' parameter in the topic allows the client to choose the payload
format it will send/receive. For the supported values of 'TYPE' see the
'Payloads' section below.

### Limitations

The current implementation is quite basic, and in particular:

-   Authentication is not supported
-   Only QoS level 0 is supported

### Payloads

XMPP payloads are always XML, but MQTT does not define a payload format.
Therefore mod\_pubsub\_mqtt has some built-in data format translators.

Currently supported data types:

-   `json`: See [XEP-0335](http://xmpp.org/extensions/xep-0335.html) for
    the format.
-   `utf8`: Plain UTF-8 text (wrapped inside
    `<data xmlns="https://prosody.im/protocol/mqtt"/>`)
-   `atom_title`: Returns the title of an Atom entry as UTF-8 data

Configuration
-------------

There is no special configuration for this module. Simply load it on
your pubsub host like so:

    Component "pubsub.example.org" "pubsub"
        modules_enabled = { "pubsub_mqtt" }

You may also configure which port(s) mod\_pubsub\_mqtt listens on using
Prosody's standard config directives, such as `mqtt_ports` and
`mqtt_tls_ports`. Network settings **must** be specified in the global section
of the config file, not under any particular pubsub component. The default
port is 1883 (MQTT's standard port number) and 8883 for TLS connections.

Compatibility
-------------

  ------- --------------
  trunk   Works
  0.12    Works
  ------- --------------
