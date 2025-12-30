# Introduction

This module adds newly registered users as members to a specified MUC
room and sends them an invite. In a way, this is similar in purpose to
[mod_support_contact] and [mod_default_bookmarks].

# Example

    VirtualHost"example.com"
        modules_enabled = { "support_room" }
        support_room = "room@muc.example.com"
        support_room_inviter = "support@example.com"
        support_room_reason = "Invite new users to the support room"

    Component "muc.example.com"

# Compatibility

This module

  Version   Works
  --------- -------
  0.11.x    Yes
  0.10.x    No
