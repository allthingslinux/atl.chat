---
labels:
- 'Stage-Alpha'
summary: 'XEP-XXX: Cloud push notifications for MUC'
---

# Introduction

This is an experimental fork of [mod_cloud_notify](https://modules.prosody.im/mod_cloud_notify.html)
which allows a [XEP-0357 Push Notifications App Servers](https://xmpp.org/extensions/xep-0357.html#general-architecture)
to be registered against a MUC domain (normally they're only registered against
your own chat server's domain).

The goal here is to also enable push notifications also for MUCs.

In contrast to mod_cloud_notify, this module does NOT integrate with
mod_smacks, because a MUC can't access a remote user's XEP-0198 queue.

Configuration
=============

  Option                               Default           Description
  ------------------------------------ ----------------- -------------------------------------------------------------------------------------------------------------------
  `push_notification_with_body`        `false`           Whether or not to send the message body to remote pubsub node.
  `push_notification_with_sender`      `false`           Whether or not to send the message sender to remote pubsub node.
  `push_max_errors`                    `16`              How much persistent push errors are tolerated before notifications for the identifier in question are disabled
  `push_notification_important_body`   `New Message!`    The body text to use when the stanza is important (see above), no message body is sent if this is empty
  `push_max_devices`                   `5`               The number of allowed devices per user (the oldest devices are automatically removed if this threshold is reached)

There are privacy implications for enabling these options because
plaintext content and metadata will be shared with centralized servers
(the pubsub node) run by arbitrary app developers.

## To test this module:

The [Converse](http://conversejs.org/) client has support for registering push
"app servers" against a MUC.

You specify app servers with the [push_app_servers](https://conversejs.org/docs/html/configuration.html#push-app-servers)
config setting.

And then you need to set [enable_muc_push](https://conversejs.org/docs/html/configuration.html#enable-muc-push)
to `true` so that these app servers are also registered against MUC domains.

Additionally you need to set [auto_register_muc_nickname](https://conversejs.org/docs/html/configuration.html#auto-register-muc-nickname)
to true.

Then, when you enter a MUC, Converse will try to automatically register your nickname
on that MUC.

Note: Converse currently doesn't let you register separate app servers for
a MUC domain. The same app servers are registered for the MUC domain and your
own domain.

## To be done:

We currently don't handle "ghost connections", users who are currently offline
but the XMPP server is not yet aware of this and shows considers them online in
the MUC.

Prosody already checks for error bounces from undelivered groupchat messages
and then kicks the particular user from the room.

So these ghost connection users eventually get kicked from the room.

We now need a module that fires an event when a groupchat messages can't be
delivered to an occupant. The module can look up the undelivered message in MAM
and include it in the event.

In mod_muc_cloud_notify we can then listen for this event and send out a push
notification.
