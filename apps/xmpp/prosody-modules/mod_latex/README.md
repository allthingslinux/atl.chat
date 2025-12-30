---
labels:
- 'Stage-Beta'
summary: Replace LaTeX markup in messages with embedded images
...

Introduction
============

This module intercepts messages between users and into chatrooms, and
attaches a links to a rendered version of any
[LaTeX](http://en.wikipedia.org/wiki/LaTeX) in the message. This
requires client support for
[XHTML-IM](http://xmpp.org/extensions/xep-0071.html), and fetching
images via HTTP.

This module was tested with the [Gajim](http://gajim.org/) client.

Details
=======

There is no configuration (yet). The module uses
[MathTran](http://www.mathtran.org/) to render the LaTeX.

Todo
====

-   Support for other rendering services (easy)
-   Provide a built-in rendering service (e.g. mimetex)
-   Send the images inline over XMPP (little client support at the
    moment)

Compatibility
=============

  ----- -------
  0.6   Works
  0.7   Works
  ----- -------
