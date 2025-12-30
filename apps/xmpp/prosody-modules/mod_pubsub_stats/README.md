---
labels:
- 'Statistics'
...

This module publishes data from [Prosody's `internal` statistics][doc:statistics]
 into a PubSub node in [XEP-0039] format.

The node defaults to `stats` but can be changed with the option
`pubsub_stats_node`.

``` lua
Component "pubsub.example.com" "pubsub"
modules_enabled = {
    "pubsub_stats";
}
pubsub_stats_node = "statistics"
```
