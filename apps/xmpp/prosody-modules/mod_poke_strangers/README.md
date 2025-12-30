---
labels:
- 'Stage-Alpha'
summary: 'Query the features and version of JIDs sending messages to contacts they are not subscribed to.'
...

Introduction
============

In order to build heuristics for which messages are spam, it is necessary to
log as many details as possible about the spammers. This module sends a
version and disco query whenever a message is received from a JID to a user it
is not subscribed to. The results are printed to Prosody's log file at the
'info' level. Queried full JIDs are not queried again until Prosody restarts.

The queries are sent regardless of whether the local user exists, so it does
not reveal if an account is active.

Compatibility
=============

  ----- -------
  0.9   Works
  ----- -------
