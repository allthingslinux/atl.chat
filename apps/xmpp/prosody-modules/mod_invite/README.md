---
labels:
- 'Stage-Deprecated'
summary: 'Allows users to invite new users'
...

**NOTE:** This module has been deprecated. Its functionality has been
moved to other modules, see the mod_invites documentation for details.

Introduction
============

This module allows users with an account to generate single-use invite URLs
using an ad-hoc command. The invite URLs allow new users to create an account
even if public registration is disabled.

After the account is created, the inviter and the invitee are automatically
added to the other's roster. The inviter of a user is stored, so can be used
later (for example, for detecting spammers).

This module depends on Prosody's internal webserver.

Compatibility
=============

  ----- -------
  0.9   Works
  ----- -------
