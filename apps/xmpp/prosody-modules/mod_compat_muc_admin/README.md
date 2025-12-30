---
labels:
- 'Stage-Beta'
summary: |
    COMPAT Module for old clients using wrong namespaces in MUC's
    affiliation manipulations.
...

Details
=======

Adds compatibility for old clients/libraries attempting to change
affiliations and retrieve 'em sending the \<
http://jabber.org/protocol/muc\#owner \> xmlns instead of \<
http://jabber.org/protocol/muc\#admin \>.

Usage
=====

Copy the plugin into your prosody's modules directory.

And add it between the enabled muc component's modules

Compatibility
=============

-   0.7-0.8.x
