---
labels:
- 'Stage-Alpha'
summary: 'XEP-0273: Stanza Interception and Filtering Technology'
...

Introduction
============

[SIFT][XEP-0273] is a technology to allow clients to filter incoming
traffic on the server. This helps save bandwidth, etc.

Compatibility
=============

  ----- -------
  0.7   Works
  ----- -------

Quirks
======

This implementation is a work in progress.

-   Stanzas to full JIDs get sifted correctly
-   Stanzas to bare JIDs are currently allowed/disallowed for all
    resources as a whole, and not for individual resources
-   Presence is only sent to available resources, and probes are not
    sent for unavailable reasources
-   This module currently does not interact with offline messages
    (filtered messages are dropped with an error reply)
-   Not tested with privacy lists
