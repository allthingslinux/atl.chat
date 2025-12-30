Introduction
============

This module attempts to sanitize XHTML-IM messages.

It does **not** attempt to sanitize any CSS embedded in `style`
attributes, these are instead stripped by default.

Configuration
=============

  Option                   Type      Default
  ------------------------ --------- ---------
  `strip_xhtml_style`      boolean   `true`
  `bounce_invalid_xhtml`   boolean   `false`
