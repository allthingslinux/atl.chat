---
labels:
- 'Stage-Stable'
summary: 'Close idle server-to-server connections'
...

Introduction
============

By default prosody does not close s2s
connections. This module changes that
behaviour by introducing an idle timeout.
It will close server-to-server connections
after they have been silent for a while.

Configuration
=============

The default timeout is 300 seconds (5 minutes).
To change this simply put in the config:

	s2s_idle_timeout = 180 -- time in seconds

Compatibility
=============

  Prosody Version   Status
  ----------------- ------------------------
  trunk             Works as of 2025-06-13
  13.0              Works
  0.12              Works
