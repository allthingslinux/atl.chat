---
labels:
- Stage-Beta
summary: Silly little module to convert your conversations to "swedish"
...

Introduction
============

This module does some conversions on message bodys passed through it causing them to look like our beloved swedish chef had typed them.

Details
=======

To load this on a MUC component do

    Component "funconference.example.com" "muc"
        modules_enabled = { "swedishchef" }
        swedishchef_trigger = "!chef"; -- optional, converts only when the message starts with "!chef"

This also works for whole servers, it is not recommended ;)

Compatibility
=============

Prosody-Version Status
--------------- --------------------
trunk           Works as of 24-12-20
0.12            Works

Todo
====

-   Possibly add xhtml-im (XEP-0071) support
