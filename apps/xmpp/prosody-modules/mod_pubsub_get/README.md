---
labels:
    - "Stage-Alpha"
summary: Get pubsub items via HTTP GET
---

# Introduction

WARNING: this module does not implement any type of access control and will effectively make all
pubsub data public on the component it is loaded onto.

This module lets you fetch the items of a specific pubsub node via an HTTP GET request.
I implemented it for a read-only view of comments published according to XEP-0277.

# Configuration

Nothing is configurable, just load the module on a specific component.

```lua
Component "comments.example.com" "pubsub"
    modules_enabled = { "pubsub_get" }
```

# Use

To query the items of the node "urn:xmpp:microblog:0:comments/some-article", issue a GET for
`https://comments.example.com:5281/pubsub_get?node=urn:xmpp:microblog:0:comments/some-article`.
This will return a JSON object containing the items data.

# TODO

-   Only return items with "open" access model

# Compatibility

Requires Prosody trunk / 0.12
