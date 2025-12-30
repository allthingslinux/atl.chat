---
labels:
- 'Stage-Alpha'
summary: 'Store who created the invite to create a user account'
...

Introduction
============

Invites are an intermediate way between opening registrations completely and
closing registrations completely.

By letting users invite other users to the server, an administrator exposes
themselves again to the risk of abuse.

To combat that abuse more effectively, this module allows to store (outside
of the user’s information) who created an invite which was used to create the
user’s account.

Details
=======

Add it to `modules_enabled`.

Assuming file based storage the information will be stored at your storage location under `./invites_tracking/` 

Caveats
=======

- The information is not deleted even when the associated user accounts are
  deleted.
- Currently, there is no integrated way to make use of that information.

Compatibility
=============

Prosody-Version Status
--------------- ---------------------
trunk           Works as of 24-12-08
0.12            unknown
