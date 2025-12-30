# Introduction

This module lets you programmatically subscribe to updates from a
[pubsub][xep0060] node, even if the pubsub service is remote.

## Example

``` {.lua}
module:depends("pubsub_subscription");
module:add_item("pubsub-subscription", {
    service = "pubsub.example.com";
    node = "otter_facts";

    -- Callbacks:
    on_subscribed = function()
        module:log("info", "Otter facts incoming!");
    end;

    on_item = function(event)
        module:log("info", "Random Otter Fact: %s", event.payload:get_text());
    end;
});
```

## Usage

Ensure the module is loaded and add your subscription via the
`:add_item` API. The item table MUST have `service` and `node` fields
and SHOULD have one or more `on_<event>` callbacks.

The JID of the pubsub service is given in `service` (could also be the
JID of an user for advanced PEP usage) and the node is given in,
unsurprisingly, the `node` field.

The various `on_event` callback functions, if present, gets called when
new events are received. The most interesting would be `on_item`, which
receives incoming items. Available events are:

`on_subscribed`
:   The subscription was successful, events may follow.

`on_unsubscribed`
:   Subscription was removed successfully, this happens if the
    subscription is removed, which you would normally never do.

`on_error`
:   If there was an error subscribing to the pubsub service. Receives a
    table with `type`, `condition`, `text`, and `extra` fields as
    argument.

`on_item`
:   An item publication, the payload itself available in the `payload`
    field in the table provided as argument. The ID of the item can be
    found in `item.attr.id`.

`on_retract`
:   When an item gets retracted (removed by the publisher). The ID of
    the item can be found in `item.attr.id` of the table argument..

`on_purge`
:   All the items were removed by the publisher.

`on_delete`
:   The entire pubsub node was removed from the pubsub service. No
    subscription exists after this.

``` {.lua}
event_payload = {
    -- Common prosody event entries:
    stanza = util.stanza;
    origin = util.session;

    -- PubSub service details
    service = "pubsub.example.com";
    node = "otter_facts";

    -- The pubsub event itself
    item = util.stanza; -- <item/>
    payload = util.stanza; -- actual payload, child of <item/>
}
```

# Compatibility

Should work with Prosody \>= 0.11.x
