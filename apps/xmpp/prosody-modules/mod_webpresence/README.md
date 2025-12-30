---
labels:
- 'Stage-Stable'
summary: Display your online status in web pages
...

Introduction
============

Quite often you may want to publish your Jabber status to your blog or
website. mod\_webpresence allows you to do exactly this.

Details
=======

This module uses Prosody's built-in HTTP server (it does not depend on
mod\_httpserver). It supplies a status icon representative of a user's
online state.

Installation
============

Simply copy mod\_webpresence.lua to your modules directory, the image
files are embedded within it. Then add "webpresence" to your
modules\_enabled list.

Usage
=====

Once loaded you can embed the icon into a page using a simple `<img>`
tag, as follows:

    <img src="http://prosody.example.com:5280/status/john.smith" />

Alternatively, it can be used to get status name as plaint text, status
message as plain text or html-code for embedding on web-pages.

To get status name in plain text you can use something like that link:
`http://prosody.example.com:5280/status/john.smith/text`

To get status message as plain text you can use something like following
link: `http://prosody.example.com:5280/status/john.smith/message`

To get html code, containig status name, status image and status message
(if set): `http://prosody.example.com:5280/status/john.smith/html`

All other

Compatibility
=============

  ----- -------
  trunk   Works
  0.10   Works
  0.9   Works
  0.8   Works
  0.7   Works
  0.6   Works
  ----- -------

Todo
====

-   Display PEP information (maybe a new plugin?)
-   More (free) iconsets
-   Internal/external image generator (GD, ImageMagick)
