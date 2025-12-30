---
labels:
- Stage-Beta
summary: Subscribe to pubsub nodes using the HTML5 EventSource API
...

Introduction
------------

[Server-Sent Events](https://en.wikipedia.org/wiki/Server-sent_events)
is a simple HTTP/line-based protocol supported in HTML5, making it easy
to receive a stream of "events" in realtime using the Javascript
[EventSource
API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource).

EventSource is supported in [most modern
browsers](http://caniuse.com/#feat=eventsource), and for the remainder
there are 'polyfill' compatibility layers such as
[EventSource.js](https://github.com/remy/polyfills/blob/master/EventSource.js)
and [jquery.eventsource](https://github.com/rwldrn/jquery.eventsource).

Details
-------

Subscribing to a node from Javascript is easy:

    var source = new EventSource('http://pubsub.example.org:5280/eventsource/mynode');
    source.onmessage = function (event) {
      console.log(event.data); // Do whatever you want with the data here
    };

### Cross-domain issues

The same cross-domain restrictions apply to EventSource that apply to
BOSH, and support for CORS is not clearly standardized yet. You may want
to proxy connections through your web server for this reason. See [BOSH:
Cross-domain
issues](https://prosody.im/doc/setting_up_bosh#proxying_requests) for
more information.

Configuration
-------------

There is no special configuration for this module. Simply load it onto a
pubsub component like so:

    Component "pubsub.example.org" "pubsub"
      modules_enabled = { "pubsub_eventsource" }

As it uses HTTP to serve the event streams, you can use Prosody's
standard [HTTP configuration options](https://prosody.im/doc/http) to
control how/where the streams are served.

**Note about URLs:** It is important to get the event streams from the
correct hostname (that of the pubsub host). An example stream URL is
`http://pubsub.example.org:5280/eventsource/mynode`. If you need to
access the streams using another hostname (e.g. `example.org`) you can
use the `http_host` option under the Component, e.g.
`http_host = "example.org"`. For more information see the ['Virtual
Hosts'](https://prosody.im/doc/http#virtual_hosts) section of our HTTP
documentation.

Compatibility
-------------

  ------- --------------
  0.9     Works
  0.8     Doesn't work
  Trunk   Works
  ------- --------------
