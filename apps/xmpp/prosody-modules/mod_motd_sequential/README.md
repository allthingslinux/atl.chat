---
labels:
- 'Stage-Beta'
summary: Sequential MOTD messages
...

Introduction
============

mod\_motd\_sequential is a variant of
[mod\_motd](https://prosody.im/doc/modules/mod_motd) that lets you
specify a sequence of MOTD messages instead of a single static one. Each
message is only sent once and the module keeps track of who as seen
which message.

Configuration
=============

``` lua
modules_enabled = {
  -- other modules
    "motd_sequential";
}
motd_sequential_messages = {
  "Hello and welcome to our service!", -- First login
  "Lorem ipsum dolor sit amet", -- Second time they login
  -- Add more messages here.
}
```
