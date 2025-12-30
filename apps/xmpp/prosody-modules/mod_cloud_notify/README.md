---
labels:
- 'Stage-Beta'
summary: 'XEP-0357: Cloud push notifications'
---

# Introduction

This module enables support for sending "push notifications" to clients
that need it, typically those running on certain mobile devices.

As well as this module, your client must support push notifications (the
apps that need it generally do, of course) and the app developer's push
gateway must be reachable from your Prosody server (this happens over a
normal XMPP server-to-server 's2s' connection).

# Details

Some platforms, notably Apple's iOS and many versions of Android, impose
limits that prevent applications from running or accessing the network
in the background. This makes it difficult or impossible for an XMPP
application to remain reliably connected to a server to receive
messages.

In order for messaging and other apps to receive notifications, the OS
vendors run proprietary servers that their OS maintains a permanent
connection to in the background. Then they provide APIs to application
developers that allow sending notifications to specific devices via
those servers.

When you connect to your server with an app that requires push
notifications, it will use this module to set up a "push registration".
When you receive a message but your device is not connected to the
server, this module will generate a notification and send it to the push
gateway operated by your application's developers). Their gateway will
then connect to your device's OS vendor and ask them to forward the
notification to your device. When your device receives the notification,
it will display it or wake up the app so it can connect to XMPP and
receive any pending messages.

This protocol is described for developers in [XEP-0357: Push
Notifications].

For this module to work reliably, you must have [mod_smacks],
[mod_mam] and [mod_carbons] also enabled on your server.

Some clients, notably Siskin and Snikket iOS need some additional
extensions that are not currently defined in a standard XEP. To support
these clients, see [mod_cloud_notify_extensions].

# Configuration

  Option                                 Default          Description
  -------------------------------------- ---------------- -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  `push_notification_important_body`     `New Message!`   The body text to use when the stanza is important (see above), no message body is sent if this is empty
  `push_max_errors`                      `16`             How much persistent push errors are tolerated before notifications for the identifier in question are disabled
  `push_max_devices`                     `5`              The number of allowed devices per user (the oldest devices are automatically removed if this threshold is reached)
  `push_max_hibernation_timeout`         `259200` (72h)   Number of seconds to extend the smacks timeout if no push was triggered yet (default: 72 hours)
  `push_notification_with_body` (\*)     `false`          Whether or not to send the real message body to remote pubsub node. Without end-to-end encryption, enabling this may expose your message contents to your client developers and OS vendor. Not recommended.
  `push_notification_with_sender` (\*)   `false`          Whether or not to send the real message sender to remote pubsub node. Enabling this may expose your contacts to your client developers and OS vendor. Not recommended.

(\*) There are privacy implications for enabling these options.[^1]

# Internal design notes

App servers are notified about offline messages, messages stored by
[mod_mam] or messages waiting in the smacks queue. The business rules
outlined
[here](//mail.jabber.org/pipermail/standards/2016-February/030925.html)
are all honored[^2].

To cooperate with [mod_smacks] this module consumes some events:
`smacks-ack-delayed`, `smacks-hibernation-start` and
`smacks-hibernation-end`. These events allow this module to send out
notifications for messages received while the session is hibernated by
[mod_smacks] or even when smacks acknowledgements for messages are
delayed by a certain amount of seconds configurable with the
[mod_smacks] setting `smacks_max_ack_delay`.

The `smacks_max_ack_delay` setting allows to send out notifications to
clients which aren't already in smacks hibernation state (because the
read timeout or connection close didn't already happen) but also aren't
responding to acknowledgement request in a timely manner. This setting
thus allows conversations to be smoother under such circumstances.

The new event `cloud-notify-ping` can be used by any module to send out
a cloud notification to either all registered endpoints for the given
user or only the endpoints given in the event data.

The config setting `push_notification_important_body` can be used to
specify an alternative body text to send to the remote pubsub node if
the stanza is encrypted or has a body. This way the real contents of the
message aren't revealed to the push appserver but it can still see that
the push is important. This is used by Chatsecure on iOS to send out
high priority pushes in those cases for example.

# Compatibility

**Note:** This module should be used with Lua 5.2 and higher. Using it
with Lua 5.1 may cause push notifications to not be sent to some
clients.

  ------- ----------------------
  trunk   Works as of 25-06-13
  13.0    Works
  0.12    Works
  ------- ----------------------

[^1]: The service which is expected to forward notifications to
    something like Google Cloud Messaging or Apple Notification Service

[^2]: [business_rules.md](//hg.prosody.im/prosody-modules/file/tip/mod_cloud_notify/business_rules.md)
