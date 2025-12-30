---
labels:
- 'Stage-Alpha'
summary: 'Automatically reserve nicknames of MUC users'
...

Introduction
============

This module automatically reserves the nickname of a user when they first join
a MUC. That's all.

Details
=======

The module doesn't currently update the registration if the user changes their
nick. That could cause flip-flopping if the user has two clients in regular
use with different nicks configured.

Compatibility
=============

Requires Prosody trunk (0.12) for the API introduced in commit
[0e7dedd8b18d](https://hg.prosody.im/trunk/rev/0e7dedd8b18d) and
[e0b58717f0c5](https://hg.prosody.im/trunk/rev/e0b58717f0c5).
