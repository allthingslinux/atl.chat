# Introduction

This module intercepts messages sent to a MUC, looks in the message's body if a user was mentioned and injects a mention type reference to that user implementing [XEP-0372](https://xmpp.org/extensions/xep-0372.html#usecase_mention)

## Features

1. Multiple mentions in the same message using affixes, including multiple mentions to the same user.
   Examples:  
   `Hello nickname`  
   `@nickname hey!`  
   `nickname, hi :)`  
   `Are you sure @nickname?`  

2. Mentions are only injected if no mention was found in a message, avoiding this way, injecting mentions in messages sent from clients with mentions support.

3. Configuration settings for customizing affixes and enabling/disabling the module for specific rooms.


# Configuring

## Enabling

```{.lua}

Component "rooms.example.net" "muc"

modules_enabled = {
    "muc_inject_mentions";
}

```

## Settings

Apart from just writing the nick of an occupant to trigger this module,
common affixes used when mentioning someone can be configured in Prosody's config file.  
Recommended affixes:

```
muc_inject_mentions_prefixes = {"@"} -- Example: @bob hello!
muc_inject_mentions_suffixes = {":", ",", "!", ".", "?"} -- Example: bob! How are you doing?
```

This module can be enabled/disabled for specific rooms.
Only one of the following settings must be set.

```
-- muc_inject_mentions_enabled_rooms = {"room@conferences.server.com"}
-- muc_inject_mentions_disabled_rooms = {"room@conferences.server.com"}
```

If none of these is set, all rooms in the muc component will have mentions enabled.


By default, if a message contains at least one mention,
the module does not do anything, as it believes all mentions were already sent by the client.
In cases where it is desired the module to inspect the message and try to find extra mentions
that could be missing, the following setting can be added:

```
muc_inject_mentions_append_mentions = true
```


Prefixes can be removed using:
```
muc_inject_mentions_strip_out_prefixes = true
```
Turning `Hey @someone` into `Hey someone`.
Currently, prefixes can only be removed from module added mentions.
If the client sends a mention type reference pointing to a nickname using a prefix (`Hey @someone`), the prefix will not be removed.


There are two lists where this module pulls the participants from.
1. Online participants
2. Participants with registered nicknames

By default, the module will try to find mentions to online participants.
Using:
```
muc_inject_mentions_reserved_nicks = true
```
Will try to find mentions to participants with registered nicknames.
This is useful for setups where the nickname is reserved for all participants,
allowing the module to catch mentions to participants that might not be online at the moment of sending the message.


It is also possible to modify how this module detects mentions.
In short, the module will detect if a mention is actually a mention
if the nickname (with or without affixes) is between spaces, new lines, or at the beginning/end of the message.
This can be changed using:

```
-- muc_inject_mentions_mention_delimiters =  {" ", "", "\n", "\t"}
```
Generally speaking and unless the use-case is very specific, there should be no need to modify the defaults of this setting.

When triggering a mention must only happen if that mention includes a prefix, this can be configured with:
```
-- muc_inject_mentions_prefix_mandatory = true
```

By default, mentions use the bare jid of the participant as the URI attribute.
If the MUC jid of the participant (eg. room@chat.example.org/Romeo) is preferred, this can be set using:
```
-- muc_inject_mentions_use_real_jid = false
```


# Example stanzas

Alice sends the following message

```
<message id="af6ca" to="room@conference.localhost" type="groupchat">
    <body>@bob hey! Are you there?</body>
</message>
```

Then, the module detects `@bob` is a mention to `bob` and injects a mention type reference to him

```
<message from="room@conference.localhost/alice" id="af6ca" to="alice@localhost/ThinkPad" type="groupchat">
    <body>@bob hey! Are you there?</body>
    <reference xmlns="urn:xmpp:reference:0"
        begin="1"
        end="3"
        uri="xmpp:bob@localhost"
        type="mention"
    />
</message>
```
