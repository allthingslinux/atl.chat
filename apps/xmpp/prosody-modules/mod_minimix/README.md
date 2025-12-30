# Account based MUC joining

Normally when joining a MUC groupchat, it is each individual client that
joins. This means their presence in the group is tied to the session,
which can be short-lived or unstable, especially in the case of mobile
clients.

This has a few problems. For one, for every message to the groupchat, a
copy is sent to each joined client. This means that at the account
level, each message would pass by once for each client that is joined,
making it difficult to archive these messages in the users personal
archive.

A potentially better approach would be that the user account itself is
the entity that joins the groupchat. Since the account is an entity that
lives in the server itself, and the server tends to be online on a good
connection most of the time, this may improve the experience and
simplify some problems.

This is one of the essential changes in the MIX architecture, which is
being designed to replace MUC.

`mod_minimix` is an experiment meant to determine if things can be
improved without replacing the entire MUC standard. It works by
pretending to each client that nothing is different and that they are
joining MUCs directly, but behind the scenes, it arranges it such that
only the account itself joins each groupchat. Which sessions have joined
which groups are kept track of. Groupchat messages are then forked to
those sessions, similar to how normal chat messages work.

## Known issues

-   You can never leave.
-   You will never see anyone leave.
-   Being kicked is not handled.

## Unknown issues

-   Probably many.

## TODO

-   Integrate with bookmarks
-   tracking outgoing presence
-   leaving rooms
-   nickname management
-   bookmark sync

# Compatibility

Briefly tested with Prosody trunk (as of this writing).
