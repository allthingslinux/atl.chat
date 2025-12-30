---
labels:
- 'Stage-Beta'
summary: Forward offline messages via email
...

Introduction
============

Quite often when I am out and about, I'm not able to connect to Jabber.
It is usually much more likely I can access my email though (whether via
the web, or a mobile client).

For this reason I decided it would be extremely useful to have Jabber
messages sent to me while I was offline forwarded to my email inbox.

Usage
=====

Simply add "offline\_email" to your modules\_enabled list. When any user
receives a message while they are offline, it will automatically be
forwarded via mail to the **same** address as their Jabber ID. e.g.
user1@example.com's offline messages will be forwarded to
user1@example.com's email inbox.

Configuration
=============

  Option                   Description
  ------------------------ ----------------------------------------------------------------------------------------------------------------------------------------------------
  queue\_offline\_emails   The number of seconds to buffer messages for, before they are sent as an email. The default is to send each message as it arrives.
  smtp\_server             Address of the SMTP server to send through. Default 'localhost' (recommended, see caveats below)
  smtp\_username           If set, Prosody will authenticate with the SMTP server before sending (default is no authentication)
  smtp\_password           The password for the above user (default is none)
  smtp\_from               Address from which it will appear the emails came. Default is smtp\_username@smtp\_server, where smtp\_username is replaced with 'xmpp' if not set

Compatibility
=============

  ----- -------
  0.9   Works
  ----- -------

Caveats/Todos/Bugs
==================

-   Currently SMTP sending blocks the whole server. This should not be
    noticeable if your mail server is on the same machine as Prosody.
-   There is not (yet) any way to configure forwarding to an email
    address other than your JID (idea... use email address in vcard?)
-   Enable/disable this feature per user?
