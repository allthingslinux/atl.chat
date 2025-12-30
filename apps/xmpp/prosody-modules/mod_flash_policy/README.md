---
labels:
- 'Stage-Alpha'
summary: Adds support for flash socket policy
...

Introduction
============

This Prosody plugin adds support for flash socket policies. When
connecting with a flash client (from a webpage, not an exe) to prosody
the flash client requests for an xml "file" on port 584 or the
connecting port (5222 in the case of default xmpp). Responding on port
584 is tricky because it requires root priviliges to set up a socket on
a port \< 1024.

This plugins filters the incoming data from the flash client. So when
the client connects with prosody it immediately sends a xml request
string (`<policy-file-request/>\0`). Prosody responds with a flash
cross-domain-policy. See
http://www.adobe.com/devnet/flashplayer/articles/socket\_policy\_files.html
for more information.

Usage
=====

Add "flash\_policy" to your modules\_enabled list.

Configuration
=============

  --------------------- --------------------------------------------------------------------------------
  crossdomain\_file     Optional. The path to a file containing an cross-domain-policy in xml format.
  crossdomain\_string   Optional. A cross-domain-policy as string. Should include the xml declaration.
  --------------------- --------------------------------------------------------------------------------

Both configuration options are optional. If both are not specified a
cross-domain-policy with "`<allow-access-from domain="*" />`" is used as
default.

Compatibility
=============

  ----- -------
  0.7   Works
  ----- -------

Caveats/Todos/Bugs
==================

-   The assumption is made that the first packet received will always
    contain the policy request data, and all of it. This isn't robust
    against fragmentation, but on the other hand I highly doubt you'll
    be seeing that with such a small packet.
-   Only tested by me on a single server :)
