---
labels:
summary: Default bookmarked chatrooms
...

Introduction
============

This module allows you to add default bookmarks for users. It only kicks
in when the user has no existing bookmarks, so users are free to add,
change or remove them.

Details
=======

Most clients support storing a private list of room "bookmarks" on the
server. When they log in, they fetch this list and join any that are
marked as "autojoin". If this list is empty, as it would be for new
users, this module would return the list supplied in the config.

Configuration
=============

Add "default\_bookmarks" to your modules\_enabled list:

        modules_enabled = {
                   -- ...other modules here... --
                   "default_bookmarks";
                   -- ...maybe some more here... --
        }

Then add a list of the default rooms you want:

``` lua
default_bookmarks = {
    { jid = "room@conference.example.com"; name = "The Room"; autojoin = true };
    -- Specifying a password is supported:
    { jid = "secret-room@conference.example.com"; name = "A Secret Room"; password = "secret"; autojoin = true };
    -- You can also use this compact syntax:
    "yetanother@conference.example.com"; -- this will get "yetanother" as name
};
```

Compatibility
-------------

  ------- ---------------
  trunk   Works
  0.10    Should work
  0.9     Should work
  ------- ---------------
