---
summary: PubSubHubbub hub
...

Introduction
============

This module implements a
[PubSubHubbub](http://pubsubhubbub.github.io/PubSubHubbub/pubsubhubbub-core-0.3.html)
(PuSH) hub, allowing PuSH clients to subscribe to local XMPP
[Publish-Subscribe](http://xmpp.org/extensions/xep-0060.html) nodes
stored by [mod\_pubsub](http://prosody.im/doc/modules/mod_pubsub) and
receive real time updates to feeds.

Configuration
=============

    Component "pubsub.example.com" "pubsub"

    modules_enabled = {
      "pubsub_hub";
    }

The hub is then available on `http://pubsub.example.com:5280/hub`.

Compatibility
=============

  ------- --------------
  trunk   Works
  0.10    Should work
  0.9     Works
  0.8     Doesn't work
  ------- --------------


