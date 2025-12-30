---
summary: HTTP request logging
...

Introduction
============

This module logs *outgoing* requests that go via the internal net.http API.

Output format liable to change.

Configuration
=============

One option is required, set `log_http_file` to the file path you would like to log to.

Compatibility
=============

  ----- -------
  0.10   Works (requires 375cf924fce1 or later)
  ----- -------
