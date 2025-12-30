---
labels:
- Stage-Alpha
summary: XMPP-layer access control for Prosody
---

Introduction
============

This module enforces access policies using Prosody's new [roles and
permissions framework](https://prosody.im/doc/developers/permissions). It can
be used to grant restricted access to an XMPP account or services.

This module is still in its early stages, and prone to change. Feedback from
testers is welcome. At this early stage, it should not be solely relied upon
for account security purposes.

Configuration
=============

There is no configuration, apart from Prosody's normal roles and permissions
configuration.

Permissions
===========

`xmpp:federate`
:   Communicate with other users and services on other hosts on the XMPP
    network

`xmpp:account:messages:read`
:   Read incoming messages

`xmpp:account:messages:write`
:   Send outgoing messages

`xmpp:account:presence:write`
:   Update presence for the account

`xmpp:account:contacts:read`/`xmpp:account:contacts:write`
:   Controls access to the contact list (roster)

`xmpp:account:bookmarks:read`/`xmpp:account:bookmarks:write`
:   Controls access to the bookmarks (group chats list)

`xmpp:account:profile:read`/`xmpp:account:profile:write`
:   Controls access to the user's profile (e.g. vCard/avatar)

`xmpp:account:omemo:read`/`xmpp:account:omemo:write`
:   Controls access to the user's OMEMO data

`xmpp:account:blocklist:read`/`xmpp:account:blocklist:write`
:   Controls access to the user's block list

`xmpp:account:disco:read`
:   Controls access to the user's service discovery information

Compatibility
=============

Requires Prosody trunk 72f431b4dc2c (build 1444) or later.
