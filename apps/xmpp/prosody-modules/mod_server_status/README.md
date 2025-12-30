---
labels:
- 'Stage-Stable'
summary: Server status plugin
...

Introduction
============

This module fetches the current status of configured hosts and/or stanza
statistics from
[mod\_stanza\_counter](http://code.google.com/p/prosody-modules/wiki/mod_stanza_counter#).
And outputs it in either XML or JSON format.

Usage
=====

Copy the file into prosody's module directory and place it into your
global's enabled modules.

Configuration example:

    server_status_basepath = "/server-info/"
    server_status_show_hosts = { "iwanttoshowifthishostisonline.com", "iwanttoshowifthishostisonline2.com" }
    server_status_show_comps = { "muc.iwanttoshowifthishostisonline.com", "transport.iwanttoshowifthishostisonline.com" }
    server_status_json = true

By default the plugin's output is in XML, setting server\_status\_json
to "true" will turn it into JSON instead. if mod\_stanza\_counter isn't
loaded the plugin will require at least either
server\_status\_show\_hosts or server\_status\_show\_comps to be set.

Info
====

-   This is only compatible with 0.9 for older versions please look at
    the 0.8-diverge branch.
