---
labels:
- 'Stage-Alpha'
summary: Send XMPP stanzas via REST/HTTP
...

This module provides a [REST](https://en.wikipedia.org/wiki/Representational_state_transfer)ful
method for sending XMPP stanzas.

This enables you to send stanzas by making HTTP requests to `http://${prosody-url}/rest`.

**DANGER/ACHTUNG!: This module does NOT enforce any authentication or user-checking.
This means that by default stanzas can be sent *anyone* on behalf of *any* user.**

You should enable [mod_http_authentication](https://modules.prosody.im/mod_http_authentication.html),
to require authentication for calls made to this module, or alternatively, you
could use a reverse proxy like Nginx.

# To enable this module

Add `"http_rest"` to `modules_enabled`, either globally or for a particular virtual
host.

# How to test:

You can use curl to make the HTTP request to Prosody, to test whether this
module is working properly:

    curl -k http://localhost:5280/rest -u username:password -H "Content-Type: text/xml" -d '<iq to="pubsub.localhost" type="set" id="4dd1a1e3-ef91-4017-a5aa-eaba0a82eb94-1" from="user@localhost"><pubsub xmlns="http://jabber.org/protocol/pubsub"><publish node="Test mod_rest.lua"><item>Hello World!</item></publish></pubsub></iq>'
