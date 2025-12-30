---
labels:
- 'Stage-Beta'
summary: Provides a web interface to stored chatroom logs
rockspec:
  build:
    copy_directories:
      - res
      - static
...

Introduction
============

This module provides a built-in web interface to view chatroom logs
stored by [mod\_muc\_mam].

Installation
============

Same as any other module, be sure to include the HTML template
`http_muc_log.html` alongside `mod_http_muc_log.lua`.

Configuration
=============

For example:

``` lua
Component "conference.example.com" "muc"
modules_enabled = {
    "muc_mam";
    "http_muc_log";
}
storage = {
    muc_log = "sql"; -- for example
}
```

The web interface would then be reachable at the address:

    http://conference.example.com:5280/muc_log/

See [the page about Prosodys HTTP server][doc:http] for info about the
address.

## Styling

The default HTML template lives in `http_muc_log.html` in the same
directory as the module, but can be changed by setting
`http_muc_log_template` to point to a different file. The same template,
with different input is used for every view.

The module uses [util.interpolation][doc:developers:util:interpolation]
for rendering templates, with the pattern `"%b{}"` and HTML / XML
escaping enabled.

## Default view

To link to the latest day instead of calendar from the room listing
page:

```lua
http_muc_log_default_view = "latest"
```

## Inline images

Inline images can optionally be shown. This is disabled by default for
privacy reasons.

``` {.lua}
http_muc_log_show_images = true
```

## Calendar optimization

The calendar view relies on an optional part of the Prosody archive
storage API that provides a list of every valid date. If this is
unavailable then the module queries for the first and the last messages
and assumes that every date between those is valid. This may lead to
many empty pages in case the logs are sparse.

This optimization can be turned off, to get a more accurate calendar
view, but it will likely be very slow.

``` {.lua}
http_muc_log_lazy_calendar = false
```

## Pinned chatrooms

The room list page is normally sorted by address, rooms having a
description before those that don't. To override this, or pin certain
rooms to the top:

``` lua
http_muc_log_list_order = {
    "general@channels.example.com",
    "support@channels.example.com",
}
```

Compatibility
=============

Requires Prosody 0.11 or later and a storage backend with support for
stanza archives. See [mod\_storage\_muc\_log] for using legacy data from
[mod\_muc\_log].
