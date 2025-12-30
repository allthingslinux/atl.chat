---
labels:
- Stage-Alpha
summary: 'Push 2.0 - New Cloud-Notify'
---

The way forward for push notifications?  You are probably looking for
`mod_cloud_notify` for now though

See also [push2.md](https://hg.prosody.im/prosody-modules/file/tip/mod_push2/push2.md)

Configuration
=============

  Option                               Default           Description
  ------------------------------------ ----------------- -------------------------------------------------------------------------------------------------------------------
  `contact_uri`                        xmpp:server.tld   Contact information for the server operator (usually as a `mailto:` URI is preferred)
  `push_max_hibernation_timeout`       `259200` (72h)    Number of seconds to extend the smacks timeout if no push was triggered yet (default: 72 hours)
  `hibernate_past_first_push`          `true`            Keep hibernating using the `push_max_hibernation_timeout` even after first push

Internal design notes
=====================

App servers are notified about offline messages, messages stored by [mod_mam]
or messages waiting in the smacks queue.

To cooperate with [mod_smacks] this module consumes some events:
`smacks-ack-delayed`, `smacks-hibernation-start` and `smacks-hibernation-end`.
These events allow this module to send out notifications for messages received
while the session is hibernated by [mod_smacks] or even when smacks
acknowledgements for messages are delayed by a certain amount of seconds
configurable with the [mod_smacks] setting `smacks_max_ack_delay`.

The `smacks_max_ack_delay` setting allows to send out notifications to clients
which aren't already in smacks hibernation state (because the read timeout or
connection close didn't already happen) but also aren't responding to acknowledgement
request in a timely manner. This setting thus allows conversations to be smoother
under such circumstances.

Compatibility
=============

**Note:** This module should be used with Lua 5.3 and higher.

  ----- ----------------------
  trunk Works
  0.12  Does probably not work 
  ----- ----------------------
