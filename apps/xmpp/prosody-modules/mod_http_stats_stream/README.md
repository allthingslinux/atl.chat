---
depends:
- 'mod\_http'
provides:
- http
---

# Introduction

This module provides a streaming interface to [Prosodys internal statistics][doc:statistics] via
[Server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events).

## Example

```js
var evtSource = new EventSource("/stats_stream");

/*
 * An event with all current statistics in the form of a JSON object.
 * Normally sent only once, when first connected to the stream.
 */
evtSource.addEventListener("stats-full", function(e) {
	var initial_stats = JSON.parse(e.data);
	console.log(initial_stats);
}, false);

/*
 * An event containing only statistics that have changed since the last
 * 'stats-full' or 'stats-updated' event.
 */
evtSource.addEventListener("stats-updated", function(e) {
	var updated_stats = JSON.parse(e.data);
	console.log(updated_stats);
}, false);
```

# Compatibility

* Prosody \>= 0.11.0
* Trunk < [5f15ab7c6ae5](https://hg.prosody.im/trunk/rev/5f15ab7c6ae5)
