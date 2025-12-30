---
labels:
- 'Stage-Stable'
summary: Publish to PubSub nodes from via HTTP POST/WebHooks
---

# Introduction

This module is a fairly generic WebHook receiver that lets you easily
publish data to PubSub using a HTTP POST request. The payload can be
Atom feeds, arbitrary XML, or arbitrary JSON. The type should be
indicated via the `Content-Type` header.

-   JSON data is wrapped in a [XEP-0335] container.
-   An Atom feed may have many `<entry>` and each one is published as
    its own PubSub item.
-   Other XML is simply published to the item with ID `current`.

## JSON example

``` {.bash}
curl http://localhost:5280/pubsub_post/princely_musings \
    -H "Content-Type: application/json" \
    --data-binary '{"musing":"To be, or not to be: that is the question"}'
```

## Atom example

``` {.bash}
curl http://localhost:5280/pubsub_post/princely_musings \
    -H "Content-Type: application/xml" \
    --data-binary '<feed xmlns="http://www.w3.org/2005/Atom">
        <entry><title>Hello</title></entry></feed>'
```

## Simple form-data

``` {.bash}
curl http://localhost:5280/pubsub_post/princely_musings \
    --data musing="To be, or not to be: that is the question"
```

# Configuration

All settings are optional.

## Actor identification

First we have to figure out who is making the request.
This is configured on a per-node basis like this:

``` {.lua}
-- Per node secrets
pubsub_post_actors = {
    princely_musings = "hamlet@denmark.lit"
}
pubsub_post_default_actor = "nobody@nowhere.invalid"
```

`pubsub_post_default_actor` is used when trying to publish to a node
that is not listed in `pubsub_post_actors`. Otherwise the IP address
of the connection is used.

## Authentication

[WebSub](https://www.w3.org/TR/2018/REC-websub-20180123/) [Authenticated
Content
Distribution](https://www.w3.org/TR/2018/REC-websub-20180123/#authenticated-content-distribution)
authentication is used.

``` {.lua}
pubsub_post_secrets = {
    princely_musings = "shared secret"
}
pubsub_post_default_secret = "default secret"
```

`pubsub_post_default_secret` is used when trying to publish to a node
that is not listed in `pubsub_post_secrets`. Otherwise the request
proceeds with the previously identified actor.

::: {.alert .alert-danger}
If configured without a secret and a default actor that has permission
to create nodes the service becomes wide open.
:::

## Authorization

Authorization is handled via pubsub affiliations. Publishing requires an
affiliation with the _publish_ capability, usually `"publisher"`.

### Setting up affiliations

Prosodys PubSub module supports [setting affiliations via
XMPP](https://xmpp.org/extensions/xep-0060.html#owner-affiliations),
since 0.11.0, so affiliations can be configured with a capable client.

It can however be done from another plugin:

``` {.lua}
local mod_pubsub = module:depends("pubsub");
local pubsub = mod_pubsub.service;

pubsub:create("princely_musings", true);
pubsub:set_affiliation("princely_musings", true, "127.0.0.1", "publisher");
```

## Data mappings

The datamapper library added in 0.12.0 allows posting JSON and having it
converted to XML based on a special JSON Schema.

``` json
{
   "properties" : {
      "content" : {
         "type" : "string"
      },
      "title" : {
         "type" : "string"
      }
   },
   "type" : "object",
   "xml" : {
      "name" : "musings",
      "namespace" : "urn:example:princely"
   }
}
```

And in the Prosody config file:

``` lua
pubsub_post_mappings = {
    princely_musings = "musings.json";
}
```

Then, POSTing a JSON payload like

``` json
{
   "content" : "To be, or not to be: that is the question",
   "title" : "Soliloquy"
}
```

results in a payload like

``` xml
<musings xmlns="urn:example:princely">
  <title>Soliloquy</title>
  <content>To be, or not to be: that is the question</content>
</musings>
```

being published to the node.
