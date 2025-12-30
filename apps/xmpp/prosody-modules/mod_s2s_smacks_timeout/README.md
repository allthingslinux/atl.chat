---
labels:
- Stage-Obsolete
---

# Introduction

::: {.alert .alert-warning}
This behavior has now been merged into
[mod_s2s][doc:modules:mod_s2s] in trunk and is therefore obsolete
when used with trunk.

It can still be used with Prosody 0.12 to get this behavior.
:::

This module closes s2s connections when
[mod_smacks][doc:modules:mod_smacks] reports that a connection has not
received a timely acknowledgement as requested, indicating that the
connection is broken or the remote server is not responding.

With the connection closed, the next stanza to be directed to that
server will trigger Prosody to establish a new connection, instead of
queueing it on the potentially broken connection.

This should prevent messages from being stuck in a queue for a
potentially long time before being bounced back to the sender as
delivery failure reports.

Normally the amount of time it takes for a broken connection to time out
is determined by TCP.

If this is deemed sensible behavior then it will likely be merged into
Prosody itself somewhere.
