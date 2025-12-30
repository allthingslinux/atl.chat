---
labels:
- 'Stage-Alpha'
summary: Subscribe to Twitter search queries over pubsub
...

Introduction
------------

Twitter has an open 'realtime' search API, but it requires polling
(within their rate limits). This module allows Prosody to poll for you,
and push new results to subscribers over XMPP.

Configuration
-------------

This module must be loaded on a Prosody pubsub component. Add it to
`modules_enabled` and configure like so:

    Component "pubsub.example.com" "pubsub"
    modules_enabled = { "pubsub_twitter" }

    twitter_searches = {
      realtime = "xmpp OR realtime";
      prosody = "prosody xmpp";
    }

This example creates two nodes, 'realtime' and 'prosody' that clients
can subscribe to using
[XEP-0060](http://xmpp.org/extensions/xep-0060.html). Results are in
[ATOM 1.0 format](http://atomenabled.org/) for easy consumption.

  Option                    Description
  ------------------------- --------------------------------------------------------------------------------
  twitter\_searches         A list of virtual nodes to create and their associated Twitter search queries.
  twitter\_pull\_interval   Number of minutes between polling for new results (default 20)
  twitter\_search\_url      URL of the JSON search API, default: "http://search.twitter.com/search.json"

Compatibility
-------------

  ----- -------
  0.9   Works
  ----- -------
