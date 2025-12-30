---
summary: 'Allows implementing a component or bot over HTTP'
...

Introduction
============

This module allows you to implement a component that speaks HTTP. Stanzas (such as messages) coming from XMPP are sent to
a configurable URL as a HTTP POST. If the POST returns a response, that response is returned to the sender over XMPP.

See also mod_post_msg.

Example usage
-------------

Example echo bot in PHP:

``` php
<?php 

// Receive and decode message JSON
$post_data = file_get_contents('php://input');
$received = json_decode($post_data)->body;

// Send response
header('Content-Type: application/json');
echo json_encode(array(
        'body' => "Did you say $received?"
));

?>
```

Configuration
=============

The module is quite flexible, but should generally be loaded as a component like this:

```
Component "yourservice.example.com" "component_http"
  component_post_url = "https://example.com/your-api"
```

Such a component would handle traffic for all JIDs with 'yourservice.example.com' as the hostname, such
as 'foobar@yourservice.example.com'. Although this example uses a subdomain, there is no requirement for
the component to use a subdomain.

Available configuration options are:


  Option                                 Description
  ------------------------------------   -------------------------------------------------------------------------------------------------------------------------------------------------
  component\_post\_url                   The URL that will handle incoming stanzas
  component\_post\_stanzas               A list of stanza types to forward over HTTP. Defaults to `{ "message" }`.

Details
=======

Requests
--------

Each received stanza is converted into a JSON object, and submitted to `component_post_url` using a HTTP POST request.

The JSON object always has the following properties:

  Property                    Description
  --------------------------  ------------
  to                          The JID that the stanza was sent to (e.g. foobar@your.component.domain)
  from                        The sender's JID.
  kind                        The kind of stanza (will always be "message", "presence" or "iq".
  stanza                      The full XML of the stanza.

Additionally, the JSON object may contain the following properties:

  Property                    Description
  --------------------------  ------------
  body                        If the stanza is a message, and it contains a body, this is the string content of the body.


Responses
---------

If you wish to respond to a stanza, you may include a reply when you respond to the HTTP request.

Responses must have a HTTP status 200 (OK), and must set the Conent-Type header to `application/json`.

A response may contain any of the properties of a request. If not supplied, then defaults are chosen.

If 'to' and 'from' are not specified in the response, they are automatically swapped so that the reply is sent to the original sender of the stanza.

If 'kind' is not set, it defaults to 'message', and if 'body' is set, this is automatically added as a message body.

If 'stanza' is set, it overrides all of the above, and the supplied stanza is sent as-is using Prosody's normal routing rules. Note that stanzas
sent by components must have a 'to' and 'from'.

Presence
--------

By default the module automatically handles presence to provide an always-on component, that automatically accepts subscription requests.

This means that by default presence stanzas are not forwarded to the configured URL. To provide your own presence handling, you can override
this by adding "presence" to the component\_post\_stanzas option in your config.


Compatibility
=============

Should work with all versions of Prosody from 0.9 upwards.
