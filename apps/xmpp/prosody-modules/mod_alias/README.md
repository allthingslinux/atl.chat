---
summary: "Point alias accounts or domains to correct XMPP user"
labels:
- 'Stage-Alpha'
...

Introduction
============

This module allows you to set up aliases that alert people who try to
contact them or add them to their roster what your actual JID is.  This
is useful for changing JIDs, or just in the case where you own both
example.com and example.net, and want people who contact you@example.com
to be alerted to contact you at you@example.net instead.

This type of aliasing is well supported in the email world, but very hard
to handle with XMPP, this module sidesteps all the hard problems by just
sending the user a helpful message, requiring humans to decide what they
actually want to do.

This doesn't require any special support on other clients or servers,
just the ability to receive messages.

Configuration
=============

Add the module to the `modules_enabled` list.

    modules_enabled = {
        ...
        "alias";
    }

Then set up your list of aliases, aliases can be full or bare JIDs,
or hosts:

    aliases = {
        ["old@example.net"] = "new@example.net";
        ["you@example.com"] = "you@example.net";
        ["conference.example.com"] = "conference.example.net";
    }

You can also set up a custom response, by default it is:

    alias_response = "User $alias can be contacted at $target";

A script named mod_alias_postfixadmin.sh is included in this directory to
generate the aliases array directly from a postfixadmin MySQL database.
Instructions for use are included in the script.

Compatibility
=============

  ------------–----------  --------------
  trunk as of 2024-10-22   Works
  0.12                     Works
  -----------------------  --------------

