# Introduction

This module lets you manage subscriptions to pubsub nodes via simple
chat messages. Subscriptions are always added based on bare JID. The
`include_body` flag is enabled so that a plain text body version of
events can be included, where supported.

# Configuring

``` {.lua}
Component "pubsub.example.com" "pubsub"
modules_enabled = {
    "pubsub_text_interface",
}
```

# Commands

The following commands are supported. Simply send a normal chat message
to the PubSub component where this module is enabled. When subscribing
or unsubscribing, be sure to replace `node` with the node you want to
subscribe to or unsubscribe from.

-   `help` - a help message, listing these commands
-   `list` - list available nodes
-   `subscribe node` - subscribe to a node
-   `unsubscribe node` - unsubscribe from a node
-   `last node` - sends the last published item from the node to you

# Compatibility

Should work with Prosody since 0.9, when
[mod\_pubsub][doc:modules:mod_pubsub] was introduced.

The `last` command is available from Prosody 0.11.
