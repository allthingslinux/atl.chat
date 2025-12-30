---
labels:
- 'Stage-Beta'
summary: Manually override the list of service discovery items
...

Introduction
============

This Prosody plugin lets you manually override the service discovery
items for a host.

Usage
=====

Simply add `"discoitems"` to your modules\_enabled list. Then add the
`disco_items` option to hosts for which you wish to override the default
response.

Note: mod\_disco in Prosody 0.8+ supports the `disco_items` option; this
plugin changes the behavior from appending items to replacing items

Configuration
=============

The `disco_items` option can be added to relevant hosts:

    disco_items = {
      {"proxy.eu.jabber.org", "Jabber.org SOCKS5 service"};
      {"conference.jabber.org", "The Jabber.org MUC"};
    }

The format for individual items is `{JID, display-name}`. The
display-name can be omitted: `{JID}`.

Compatibility
=============

  ----- -------------
  0.8   Works
  0.7   Works
  0.6   Works
  0.5   Should work
  ----- -------------
