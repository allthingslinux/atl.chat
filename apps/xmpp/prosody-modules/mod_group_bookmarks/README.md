---
labels:
- 'Stage-Beta'
summary: 'mod\_groups for chatrooms'
...

Introduction
============

[mod\_groups](http://prosody.im/doc/modules/mod_groups) allows you to
insert contacts into users' contact lists. Well mod\_group\_bookmarks
allows you to insert chatrooms into the user's bookmarks. These are
fetched by their client and automatically joined when the log in.

In short, if you want to automatically join users to rooms when they
sign in, this is the module you want.

Details
=======

Most clients support storing a private list of room "bookmarks" on the
server. When they log in, they fetch this list and join any that are
marked as "autojoin". Without affecting normal usage of the bookmarks
store this module dynamically inserts custom rooms into users' bookmarks
lists.

Usage
=====

Similar to [mod\_groups](http://prosody.im/doc/modules/mod_groups), you
need to make a text file in this format:

    [room@conferenceserver]
    user1@example.com=User 1
    user2@example.com=User 2

    [otherroom@conferenceserver]
    user3@example.net=User 3

Add "group\_bookmarks" to your modules\_enabled list:

    modules_enabled = {
               -- ...other modules here... --
               "group_bookmarks";
               -- ...maybe some more here... --
    }

Configuration
=============

  ------------------------ ---------------------------------------------------
  group\_bookmarks\_file   The path to the text file you created (as above).
  ------------------------ ---------------------------------------------------

Compatibility
=============

  ----- -------------
  0.8   Works
  0.7   Should work
  0.6   Should work
  ----- -------------

Todo
====

-   Support for injecting into ALL users bookmarks, without needing a
    list
-   Allow turning off the autojoin flag
-   Perhaps support a friendly name for the bookmark (currently uses the
    room address)
