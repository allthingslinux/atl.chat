---
labels:
- 'Stage-Beta'
summary: Incidents Handling plugin
...

Introduction
============

This module implements
[XEP-268](http://xmpp.org/extensions/xep-0268.html).

Details
=======

It will let you manage reports, inquiries, requests and responses
through an Adhoc interface. The following new adhoc admin commands will
be available:

-   List Incidents -- List all available incidents and let's you reply
    requests.
-   Send Incident Inquiry -- Inquiry a remote server about an incident.
-   Send Incident Report -- Send an incident report to a remote server.
-   Send Incident Request -- Send an incident request to a remote
    server.

Each Adhoc form provides syntax instructions through `<desc/>` elements
(they may currently be stripped by Prosody), although it's encouraged to
read the [IODEF specifications](https://tools.ietf.org/html/rfc5070).

Usage
=====

Copy the module folder into your prosody modules directory. Place the
module between your enabled modules either into the global or a vhost
section.

Optional configuration directives:

``` {.lua}
incidents_expire_time = 86400 -- Expiral of "closed" incidents in seconds.
```

Info
====

-   to be 0.9, works.
