---
labels:
- 'Stage-Alpha'
summary: 'Allow Slack integrations to work with Prosody MUCs'
...

Introduction
============

This module provides a Slack-compatible "web hook" interface to Prosody MUCs.
Both "incoming" web hooks, which allow Slack integrations to post messages
to Prosody MUCs, and "outgoing" web hooks, which copy messages from Prosody
MUCs to Slack-style integrations by HTTP, are supported. This can also be
used, in conjunction with various Slack inter-namespace bridging tools, to
provide a bidirectional bridge between a Prosody-hosted XMPP MUC and a Slack
channel.

If you're looking for a more versatile module, consider [mod_rest]

Usage
=====

First copy the module to the prosody plugins directory.

Then add "slack\_webhooks" to your modules\_enabled list:

``` {.lua}
Component "conference.example.org" "muc"
modules_enabled = {
  "slack_webhooks",
}
```

Configuration
=============

The normal use for this module is to provide an incoming webhook to allow
integrations to post to prosody MUCs:

``` {.lua}
incoming_webhook_path = "/msg/DFSDF56587658765NBDSA"
incoming_webhook_default_nick = "Bot" -- Unless otherwise specified, posts as "Bot"
```

This allows Slack-style JSON messages posted to http://conference.example.org/msg/DFSDF56587658765NBDSA/chat to appear in the MUC chat@conference.example.org. A username field in the message is honored as the nick attached to the message; if no username is specified, the message will use the value of default_from_nick.
Specifying a string of random gibberish in the URL is important to prevent spam.

In addition, there is a second operating mode equivalent to Slack's outgoing
webhooks. This allows all messages from a set of specified chat rooms to be
routed to an external server over HTTP in the format used by Slack's
outgoing webhooks.
``` {.lua}
outgoing_webhook_routing = {
	-- Send all messages from chat@conference.example.org to
	-- a web server.
	["chat"] = "http://example.org/cgi-bin/messagedest",
}
```

Known Issues
============

The users from whom messages delivered from integrations are apparently
delivered are not, in general, members of the MUC. Other prosody modules
that try to look up information about the users who most messages, mostly
logging modules, may become confused and fail (clients all work fine because
replayed history also can come from non-present users). In at least some cases,
such as with mod_muc_mam, this can be fixed by hiding the JIDs of the
participants in the room configuration.

There are a few smaller UI issues:

* If an integration posts with the same username as a room member, there is
  no indication (like Slack's [bot] suffix) that the message is not from that
  room member.
* It is not currently possible to prevent posting to some MUCs (this is
  also true of Slack).
* It should be possible to set the webhook configuration for a room in the
  room configuration rather than statically in Prosody's configuration file.

Compatibility
=============

  Prosody Version   Status
  ----------------- -----------
  trunk[^1]         Works
  0.12              Works
  ----------------- -----------

[^1]: as of 2024-10-22

