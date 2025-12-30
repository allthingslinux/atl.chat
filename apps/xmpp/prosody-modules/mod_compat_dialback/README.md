---
summary: Workaround for Dialback with some servers that violate RFC 6120
...

This module provides a workaround for servers that do not set the `to`
attribute on stream headers, which is required per [RFC6120]:

> ## 4.7.2. to
> 
> For initial stream headers in both client-to-server and
> server-to-server communication, the initiating entity MUST include the
> 'to' attribute and MUST set its value to a domainpart that the
> initiating entity knows or expects the receiving entity to service.

As a side effect of [this issue](https://prosody.im/issues/issue/285),
Prosody 0.10 will be unable to do [Dialback][xep220] with servers that
don't follow this.

# Known servers affected

* Openfire 3.10.2 (and probably earlier versions)
