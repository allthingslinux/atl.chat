---
labels:
- 'Stage-Alpha'
summary: 'Spam filtering'
rockspec:
  build:
    modules:
      mod_anti_spam.rtbl: rtbl.lib.lua
      mod_anti_spam.trie: trie.lib.lua
depends:
  - mod_pubsub_subscription
---

This module aims to provide an all-in-one spam filter for any kind of Prosody
deployment.

## What is spam?

You're lucky if you have to ask! But it's worth explaining, so we can be clear
about what the module does (and does not).

Similar to every other popular communication network, there are people who try
to exploit XMPP for sending unsolicited messages - usually advertisements
for products and services. These people have gathered large lists of user
addresses, e.g. by searching and "scraping" websites for contact info.

If your address has not been discovered by the spammers, you won't receive any
spam. Prosody does not reveal user addresses (except, obviously, to people who
you communicate with). So to avoid it being picked up by spammers, be careful
about posting it unprotected on websites, etc.

However, if get unlucky and your address is discovered by spammers, you may
receive dozens of spam messages per day. mod_anti_spam is designed to filter
these annoying messages to prevent them from reaching you.

## How does it work?

mod_anti_spam uses a variety of techniques to identify likely spam. Just as
the behaviour of spammers changes, The exact methods used to detect spam may
evolve over time in future updates.

If the sender is in the recipient's contact list already, no filtering will be
performed.

Otherwise, if the sender is a "stranger" to the recipient, the module will
perform some checks, and decide whether to let the message or contact request
through.

### Shared block lists

mod_anti_spam can subscribe to Real-Time Block Lists (RTBLs) such as those
published by [xmppbl.org](https://xmppbl.org). This is a highly effective
measure to reduce spam from the network.

To enable this feature, you need to specify one or more compatible spam
services in the config file:

```lua
anti_spam_services = { "xmppbl.org" }
```

### Content filters

mod_anti_spam also supports optionally filtering messages with specific
content or matching certain patterns.

A list of strings to block can be specified in the config file like so:

```lua
anti_spam_block_strings = {
  -- Block messages containing the text "exploit"
  "exploit";
}
```

Alternatively, you can specify a list of [Lua patterns](https://lua.org/manual/5.4/manual.html#6.4.1).
These are similar to regular expressions you may be familiar with from tools
like grep, but differ in a number of ways. Lua patterns are faster, but have
fewer features. The syntax is not fully compatible with other more widely-used
regular expression syntaxes. Read the Lua manual for full details.

```lua
anti_spam_block_patterns = {
  -- Block OTR handshake greetings (modern XMPP clients do not use OTR)
  "^%?OTRv2?3?%?";
}
```

There are no string or pattern filters in the module by default.

## Handling reports

We recommend setting up Prosody to allow spam reporting, in case any spam
still gets through. Documentation can be found on [xmppbl.org's site](https://xmppbl.org/reports#server-operators).

## Compatibility

Compatible with Prosody 0.12 and later.
